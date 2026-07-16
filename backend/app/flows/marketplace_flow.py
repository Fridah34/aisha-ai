from sqlalchemy.orm import Session
from app.models import User, Category, Product
from app.models import MarketplaceSession, Cart
from datetime import datetime, timedelta, timezone

SESSION_TIMEOUT_MINUTES = 30

SWITCH_KEYWORDS = {"switch", "switch store", "change store", "menu", "other shops"}

NUMBERS = ["1","2", "3", "4", "5","6","7","8","9","10"]

def get_or_create_marketplace_session(phone_number: str, db: Session) -> MarketplaceSession:
    session = db.query(MarketplaceSession).filter( 
        MarketplaceSession.phone_number == phone_number
    ). first()
    if not session:
        session = MarketplaceSession(phone_number=phone_number)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session

def is_switch_command(message: str) -> bool:
    """Checked by the router BEFORE the normal selected_business_id gate,
    so a customer can switch stores even mid-conversation inside one.
    Exact-match only (kept deliberately strict rather than fuzzy) —
    customers are told the exact keyword via the store-entry hint below."""
    return message.strip().lower() in SWITCH_KEYWORDS

def reset_to_menu(session: MarketplaceSession, db: Session) -> None:
    """Kicks the session back to the top-level 'what are you looking for'
    menu. Deliberately does NOT touch the Cart table — the cart for the
    store they're leaving stays exactly as it was, keyed by
    (phone_number, business_id), so it's there if they come back."""
    session.selected_business_id = None
    session.selected_business_type = None
    session.pending_action = None
    db.commit()

def get_or_create_cart(phone_number: str, business_id: int, db: Session) -> Cart:
    cart = (
        db.query(Cart)
        .filter(Cart.phone_number == phone_number, Cart.business_id == business_id)
        .first()
    )
    if not cart:
        cart = Cart(phone_number=phone_number, business_id=business_id, items=[])
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def get_all_categories(db: Session) -> list[str]:
    """Distinct category names across ALL businesses — this is now the
    top-level 'what are you looking for' menu, replacing business_type."""
    rows = (
        db.query(Category.name)
        .filter(Category.is_active)
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]

def get_businesses_by_category(db: Session, category_name: str) -> list[User]:
    """Every active business that has an active category matching this name."""
    return (
        db.query(User)
        .join(Category, Category.user_id == User.id)
        .filter(
            Category.name == category_name,
            Category.is_active,
            User.is_active,
        )
        .distinct()
        .all()
    )


def get_categories_for_business(db: Session, user_id:int) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.is_active)
        .order_by(Category.display_order)
        .all()
    )
    
def get_products_for_category(db: Session, user_id: int, category_id: int) -> list[Product]:
    return (
        db.query(Product)
        .filter(Product.user_id == user_id, Product.category_id == category_id, Product.is_available)
        .all()
    )
    
def get_products_for_business_category(db: Session, business_id: int, category_name: str) -> list[Product]:
    """Finds this specific business's Category row matching the name the
    customer picked at the top-level menu, then returns its products.
    Needed because Category is per-business — the same name ('Dresses')
    is a different row (and different category_id) for each business."""
    category = (
        db.query(Category)
        .filter(
            Category.user_id == business_id,
            Category.name == category_name,
            Category.is_active,
        )
        .first()
    )
    if not category:
        return []
    return get_products_for_category(db, business_id, category.id)


def _format_product_list(products: list[Product]) -> str:
    if not products:
        return "We don't have items in that category right now — want to see something else?"

    lines = ["Here's what we have:", ""]
    for i, p in enumerate(products):
        emoji = NUMBERS[i] if i < len(NUMBERS) else f"{i + 1}."
        line = f"{emoji} *{p.name}* — Ksh {p.price}"
        if p.unit:
            line += f" / {p.unit}"
        if p.variant_label and p.variant_options:
            line += f"\n   {p.variant_label}: {p.variant_options}"
        if p.description:
            line += f"\n   {p.description}"
        lines.append(line)
    lines.append("")
    lines.append("Reply with a product name or number to see photos and order.")
    return "\n".join(lines)

def resolve_product_choice(business_id: int, category_name: str, message: str, db: Session) -> Product | None:
    """Matches a customer's reply (number or name) against the product list
    they were just shown for this business/category. Returns None if no
    match — caller should then let the message flow through normally
    rather than trap the customer against a stale list."""
    products = get_products_for_business_category(db, business_id, category_name)
    names = [p.name for p in products]
    choice = _resolve_choice(message, names)
    if choice is None:
        return None
    return next((p for p in products if p.name == choice), None)

def format_numbered_list(items: list, label_fn) -> str:
    """Turns a list into '1 Name\n2 Name...' — reused at every step."""
    return "\n".join(f"{i+1} {label_fn(item)}" for i, item in enumerate(items))


def handle_marketplace_step(session: MarketplaceSession, message: str, db: Session) -> str | None:
    """
    Returns a reply string if handled deterministically.
    Returns None only if something went wrong (e.g. no categories exist yet)
    — the caller should treat None as 'nothing to show, cannot proceed'.
    """
    categories = get_all_categories(db)
    if not categories:
        return "Sorry, no categories are available right now. Please try again later."

    # First-ever message from this phone number, or session was reset
    if session.pending_action is not None and session.selected_business_id is None:
        is_stale = (
            datetime.now(timezone.utc) -  session.updated_at
        ) > timedelta(minutes= SESSION_TIMEOUT_MINUTES)
        if is_stale:
            session.pending_action = None
            session.selected_business_type = None
            db.commit()
            
    if session.pending_action is None and session.selected_business_id is None:       
        session.pending_action = "select_need"
        db.commit()
        return (
            " Welcome to AISHA Marketplace!\nWhat are you looking for today?\n\n"
            + _format_numbered_list([c.title() for c in categories])
            + "\n\nReply with a number, or type the name."
        )

    if session.pending_action == "select_need":
        choice = _resolve_choice(message, [c.title() for c in categories])
        if choice is None:
            return "Sorry, please reply with a number from the list above."

        matched_category = next(c for c in categories if c.title() == choice)
        businesses = get_businesses_by_category(db, matched_category)

        if not businesses:
            return "No stores found for that category right now. Please choose another."

        session.selected_business_type = matched_category
        session.pending_action = "select_business"
        db.commit()
        return (
            "Here are stores for you:\n\n"
            + _format_numbered_list([b.business_name for b in businesses])
            + "\n\nReply with a number, or type the name."
        )

    if session.pending_action == "select_business":
        businesses = get_businesses_by_category(db, session.selected_business_type)
        choice = _resolve_choice(message, [b.business_name for b in businesses])
        if choice is None:
            return "Sorry, please reply with a number from the list above."

        chosen = next(b for b in businesses if b.business_name == choice)
        session.selected_business_id = chosen.id
        session.pending_action = "awaiting_product_choice"
        db.commit()
        # Ensure a cart exists for this store the moment they enter it,
        # so downstream "add to cart" logic never has to create-or-fetch.
        get_or_create_cart(session.phone_number, chosen.id, db)
        products = get_products_for_business_category(db, chosen.id, session.selected_business_type)
        product_text = _format_product_list(products)

        return (
            f"Welcome to {chosen.business_name}! Here's what we have in "
            f"{session.selected_business_type}:\n\n"
            + product_text
            + "\n\n_Tip: reply 'menu' anytime to browse other stores._"
        )

    return None

def _format_numbered_list(items: list[str]) -> str:
    lines = []
    for i, item in enumerate(items):
        emoji = NUMBERS[i] if i < len(NUMBERS) else f"{i + 1}."
        lines.append(f"{emoji} {item}")
    return "\n".join(lines)


def _resolve_choice(text: str, options: list[str]):
    text = text.strip().lower()
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return options[idx]
        return None
    for opt in options:
        if opt.lower() == text:
            return opt
    return None
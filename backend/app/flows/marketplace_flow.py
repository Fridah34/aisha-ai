from sqlalchemy.orm import Session
from app.models import User, Category, Product, ConversationState


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

def get_business_types(db:Session) -> list[ str ]:
    """Distinct business types available- becomes the 'what are you looking for' menu."""
    rows =  db.query(User.business_type).distinct().all()
    return [r[0] for r in rows if r[0]]

def get_businesses_by_type(db: Session, business_type:str) -> list [User]:
    return db.query(User).filter(User.business_type == business_type, User.is_active == True).all()


def get_categories_for_business(db: Session, user_id:int) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.is_active == True)
        .order_by(Category.display_order)
        .all()
    )
    
def get_products_for_category(db: Session, user_id: int, category_id: int) -> list[Product]:
    return (
        db.query(Product)
        .filter(Product.user_id == user_id, Product.category_id == category_id, Product.is_available == True)
        .all()
    )


def format_numbered_list(items: list, label_fn) -> str:
    """Turns a list into '1 Name\n2 Name...' — reused at every step."""
    return "\n".join(f"{i+1} {label_fn(item)}" for i, item in enumerate(items))


def handle_marketplace_step(session: MarketplaceSession, message: str, db: Session) -> str | None:
    """
    Returns a reply string if handled deterministically.
    Returns None only if something went wrong (e.g. no business types exist yet)
    — the caller should treat None as 'nothing to show, cannot proceed'.
    """
    types = get_business_types(db)
    if not types:
        return "Sorry, no stores are available right now. Please try again later."

    # First-ever message from this phone number, or session was reset
    if session.pending_action is None and session.selected_business_id is None:
        session.pending_action = "select_need"
        db.commit()
        return "👋 Welcome to AISHA Marketplace!\nWhat are you looking for today?\n\n" + _format_numbered_list(
            [t.title() for t in types]
        )

    if session.pending_action == "select_need":
        choice = _resolve_choice(message, [t.title() for t in types])
        if choice is None:
            return "Sorry, please reply with a number from the list above."

        matched_type = next(t for t in types if t.title() == choice)
        businesses = get_businesses_by_type(db, matched_type)

        if not businesses:
            return "No stores found for that category right now. Please choose another."

        session.selected_business_type = matched_type
        session.pending_action = "select_business"
        db.commit()
        return "Here are stores for you:\n\n" + _format_numbered_list(
            [b.business_name for b in businesses]
        )

    if session.pending_action == "select_business":
        businesses = get_businesses_by_type(db, session.selected_business_type)
        choice = _resolve_choice(message, [b.business_name for b in businesses])
        if choice is None:
            return "Sorry, please reply with a number from the list above."

        chosen = next(b for b in businesses if b.business_name == choice)
        session.selected_business_id = chosen.id
        session.pending_action = None
        db.commit()
        return f"Welcome to {chosen.business_name}! What are you looking for today?"

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
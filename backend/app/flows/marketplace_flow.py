import re
import uuid
from datetime import datetime, timedelta, timezone

from app.models import (
    Cart,
    Category,
    Customer,
    MarketplaceSession,
    Order,
    Product,
    User,
)
from sqlalchemy import String, func
from sqlalchemy.orm import Session

SESSION_TIMEOUT_MINUTES = 30

SWITCH_KEYWORDS = {"switch", "switch store", "change store", "menu", "other shops"}
CHECKOUT_KEYWORDS = {"checkout", "check out", "done", "complete order", "finish order"}
STATUS_KEYWORDS = {
    "status",
    "order status",
    "my order",
    "track order",
    "track my order",
}

NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

# --- Pagination for Twilio List Picker (hard-capped at 10 slots) ----------
# Twilio's twilio/list-picker template is fixed at up to 10 options per
# send. Whenever a category/store list could exceed that, we show 9 real
# items + a "More options" entry in the 10th slot, and page through the
# rest on tap. Needs MarketplaceSession.list_offset (Integer, default 0) —
# see migration note in the handover doc; not optional, code below assumes
# the column exists.
PAGE_SIZE = 9
MORE_OPTIONS_LABEL = "More options"


def _get_offset(session: MarketplaceSession) -> int:
    return session.list_offset or 0


def _menu_items_for_offset(all_items: list[str], offset: int) -> list[str]:
    """Up to 10 display items: up to PAGE_SIZE real items starting at
    `offset`, plus a trailing 'More options' entry if there are more
    items beyond this page. Never returns more than 10 items total,
    which is what send_list_picker() requires."""
    page = all_items[offset : offset + PAGE_SIZE]
    has_more = (offset + PAGE_SIZE) < len(all_items)
    return page + [MORE_OPTIONS_LABEL] if has_more else page


def _resolve_paginated_choice(
    message: str, all_items: list[str], session: MarketplaceSession, db: Session
) -> tuple[str | None, list[str] | None]:
    """Resolves a reply against the CURRENT page of a paginated list.

    Returns (selection, None) if the customer picked a real item.
    Returns (None, new_display_items) if they tapped 'More options' —
    caller should resend the menu with new_display_items rather than
    treat this as a real selection.
    Returns (None, None) if the reply matched nothing on this page.
    """
    offset = _get_offset(session)
    display_items = _menu_items_for_offset(all_items, offset)
    choice = _resolve_choice(message, display_items)

    if choice == MORE_OPTIONS_LABEL:
        next_offset = offset + PAGE_SIZE
        if next_offset >= len(all_items):
            next_offset = 0  # wrap back to the first page rather than dead-end
        session.list_offset = next_offset
        db.commit()
        return None, _menu_items_for_offset(all_items, next_offset)

    return choice, None


def get_or_create_marketplace_session(
    phone_number: str, db: Session
) -> MarketplaceSession:
    session = (
        db.query(MarketplaceSession)
        .filter(MarketplaceSession.phone_number == phone_number)
        .first()
    )
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


def is_checkout_command(message: str) -> bool:
    return message.strip().lower() in CHECKOUT_KEYWORDS


def is_status_command(message: str) -> bool:
    return message.strip().lower() in STATUS_KEYWORDS


def reset_to_menu(session: MarketplaceSession, db: Session) -> None:
    """Deliberately does NOT touch the Cart table - the cart stays keyed by
    (phone_number, business_id) so it's there if they come back. Also clears
    any in-progress product/size selection so a stale pick doesn't leak into
    the next store, and resets pagination so a fresh menu always starts on
    page 1."""
    session.selected_business_id = None
    session.selected_business_type = None
    session.selected_product_id = None
    session.selected_size = None
    session.pending_action = None
    session.list_offset = 0
    db.commit()


def get_or_create_cart(phone_number: str, business_id: uuid.UUID, db: Session) -> Cart:
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
    """Distinct category names across ALL businesses — this is the
    top-level 'what are you looking for' menu, replacing business_type.
    Explicitly ordered so pagination offsets stay stable across requests —
    a DISTINCT query with no ORDER BY has no guaranteed row order, which
    would silently break "page 2" if the DB ever returned rows differently
    between the menu-send and the 'More options' tap.

    Names are stripped here, at the read source, rather than only at
    comparison time — a category saved via the dashboard as "Dress "
    (trailing space) would display as a clean "Dress" in WhatsApp's UI
    (WhatsApp trims trailing whitespace when rendering) while the actual
    string still carried the space, silently failing to match a customer's
    typed "Dress" in _resolve_choice(). Stripping once here means every
    downstream consumer (menu display, matching, anything else that reads
    categories) gets clean data automatically."""
    rows = (
        db.query(Category.name)
        .filter(Category.is_active)
        .distinct()
        .order_by(Category.name)
        .all()
    )
    return [r[0].strip() for r in rows if r[0] and r[0].strip()]


def get_businesses_by_category(db: Session, category_name: str) -> list[User]:
    """Every active business that has an active category matching this
    name. Ordered by business_name for the same pagination-stability
    reason as get_all_categories()."""
    return (
        db.query(User)
        .join(Category, Category.business_id == User.id)
        .filter(
            Category.name == category_name,
            Category.is_active,
            User.is_active,
        )
        .distinct()
        .order_by(User.business_name)
        .all()
    )


def get_categories_for_business(db: Session, business_id: uuid.UUID) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.business_id == business_id, Category.is_active)
        .order_by(Category.display_order)
        .all()
    )


def get_products_for_category(
    db: Session,
    business_id: uuid.UUID,
    category_id: uuid.UUID,
) -> list[Product]:
    return (
        db.query(Product)
        .filter(
            Product.business_id == business_id,
            Product.category_id == category_id,
            Product.is_available,
        )
        .all()
    )


def get_products_for_business_category(
    db: Session,
    business_id: uuid.UUID,
    category_name: str,
) -> list[Product]:
    """Finds this specific business's Category row matching the name the
    customer picked at the top-level menu, then returns its products.
    Needed because Category is per-business — the same name ('Dresses')
    is a different row (and different category_id) for each business."""
    category = (
        db.query(Category)
        .filter(
            Category.business_id == business_id,
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


def resolve_product_choice(
    business_id: uuid.UUID,
    category_name: str,
    message: str,
    db: Session,
) -> Product | None:
    """Matches a customer's reply (number or name) against the product list
    they were just shown for this business/category. Returns None if no
    match — caller should then let the message flow through normally
    rather than trap the customer against a stale list.

    Names are stripped before matching — same reasoning as
    get_all_categories()/store_names above: a product name saved with
    stray whitespace displays clean in WhatsApp but won't match a
    customer's typed reply unless both sides are normalized the same way."""
    products = get_products_for_business_category(db, business_id, category_name)
    names = [p.name.strip() for p in products]
    choice = _resolve_choice(message, names)
    if choice is not None:
        return next((p for p in products if p.name.strip() == choice), None)

    text_clean = message.strip().lower()
    if text_clean:
        partial_matches = [p for p in products if text_clean in p.name.strip().lower()]
        if len(partial_matches) == 1:
            return partial_matches[0]

    return None


def format_numbered_list(items: list, label_fn) -> str:
    """Turns a list into '1 Name\n2 Name...' — reused at every step."""
    return "\n".join(f"{i + 1} {label_fn(item)}" for i, item in enumerate(items))


def _parse_sizes(variant_options: str) -> list[str]:
    """Splits a comma-separated variant_options string into clean tokens.
    Matching is case-insensitive; display keeps the original casing."""
    if not variant_options:
        return []
    return [s.strip() for s in variant_options.split(",") if s.strip()]


def resolve_size_choice(text: str, variant_options: str) -> str | None:
    """Exact match only (case-insensitive) — same philosophy as category/
    store/product matching elsewhere in this file. No fuzzy matching, to
    avoid false positives against short size tokens like 'S' vs 'M'."""
    sizes = _parse_sizes(variant_options)
    text_clean = text.strip().lower()
    for s in sizes:
        if s.lower() == text_clean:
            return s

    for s in sizes:
        if re.search(rf"\b{re.escape(s.lower())}\b", text_clean):
            return s

    return None


def parse_quantity(text: str) -> int | None:
    """Digits only — deliberately does NOT treat 'yes'/'okay' as qty=1.
    A customer must state a number so we never guess how many they want."""
    text_clean = text.strip()
    if text_clean.isdigit():
        qty = int(text_clean)
        if 1 <= qty <= 100:
            return qty
    return None


def add_item_to_cart(
    cart: Cart, product: Product, size: str | None, qty: int, db: Session
) -> None:
    """Reassigns cart.items (rather than .append() in place) so SQLAlchemy's
    change-tracking on the JSON column actually detects the mutation."""
    items = list(cart.items or [])
    items.append(
        {
            "product_id": str(product.id),
            "name": product.name,
            "size": size,
            "qty": qty,
            "unit_price": float(product.price),
        }
    )
    cart.items = items
    db.commit()


def format_cart_summary(cart: Cart) -> str:
    if not cart.items:
        return "Your cart is empty."
    lines = ["Your cart:"]
    total = 0.0
    for item in cart.items:
        line_total = item["qty"] * item["unit_price"]
        total += line_total
        size_part = f" (Size {item['size']})" if item.get("size") else ""
        lines.append(
            f"- {item['qty']}x {item['name']}{size_part} — Ksh {line_total:.2f}"
        )
    lines.append(f"\nTotal: Ksh {total:.2f}")
    return "\n".join(lines)


def parse_name_and_contact(text: str) -> tuple[str, str]:
    """Deliberately not AI-driven — pulls a Kenyan-format phone number via
    regex, treats the remainder as the name. If no number is found, contact
    is left blank and the caller falls back to the customer's WhatsApp
    number (always known, since that's the channel they're messaging on)."""
    phone_match = re.search(r"(\+?254|0)[71]\d{8}", text)
    contact = phone_match.group(0) if phone_match else ""
    name = text
    if phone_match:
        name = (text[: phone_match.start()] + text[phone_match.end() :]).strip()
    name = re.sub(
        r"\b(my|contact|is|number|phone)\b", "", name, flags=re.IGNORECASE
    ).strip(" ,:-")
    return (name or "Customer"), contact


def create_orders_from_cart(
    cart: Cart, business: User, customer: Customer, name: str, contact: str, db: Session
) -> list[Order]:
    """One Order row per cart line item, all sharing one order_group_id so
    a multi-item checkout can be queried/displayed as a single unit even
    though the schema models it as N rows."""
    group_id = uuid.uuid4()
    orders = []
    for item in cart.items:
        order = Order(
            order_group_id=group_id,
            customer_id=customer.id,
            product_id=uuid.UUID(item["product_id"]),
            business_id=business.id,
            quantity=item["qty"],
            total_amount=item["qty"] * item["unit_price"],
            snapshot_customer_name=name,
            snapshot_customer_phone=contact,
            snapshot_product_name=item["name"],
            snapshot_product_price=item["unit_price"],
            snapshot_business_name=business.business_name,
        )
        db.add(order)
        orders.append(order)
    db.commit()
    return orders


def extract_order_ref(message: str) -> str | None:
    """Looks for the 8-char hex fragment we show customers as their order
    reference (e.g. 'status a1b2c3d4' or just 'a1b2c3d4'). Deliberately
    matches anywhere in the message so 'what about a1b2c3d4' still works,
    not just an exact/prefixed format."""
    match = re.search(r"\b[0-9a-fA-F]{8}\b", message)
    return match.group(0) if match else None


def get_orders_by_reference(ref: str, phone_number: str, db: Session) -> list[Order]:
    """All Order rows whose order_group_id starts with this 8-char ref,
    scoped to this customer's phone number. The phone scoping matters:
    an 8-hex-char prefix alone isn't enough entropy to treat as a secret,
    so without this filter one customer could guess/stumble onto another
    customer's order by trying short refs."""
    return (
        db.query(Order)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(
            Customer.phone_number == phone_number,
            func.cast(Order.order_group_id, String).like(f"{ref.lower()}%"),
        )
        .all()
    )


def get_latest_orders_for_customer(phone_number: str, db: Session) -> list[Order]:
    """No reference given ('status' alone) — fall back to the customer's
    most recent checkout, across any business they've ordered from."""
    latest = (
        db.query(Order)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(Customer.phone_number == phone_number)
        .order_by(Order.created_at.desc())
        .first()
    )
    if not latest:
        return []
    if not latest.order_group_id:
        return [latest]  # legacy row predating order_group_id
    return db.query(Order).filter(Order.order_group_id == latest.order_group_id).all()


def format_order_status(orders: list[Order]) -> str:
    if not orders:
        return (
            "I couldn't find an order matching that reference. Please "
            "double-check the number, or reply 'status' to see your most "
            "recent order."
        )
    ref = (
        str(orders[0].order_group_id)[:8]
        if orders[0].order_group_id
        else str(orders[0].id)
    )
    lines = [f"Order #{ref} — {orders[0].snapshot_business_name}", ""]
    for o in orders:
        lines.append(f"- {o.quantity}x {o.snapshot_product_name} — _{o.status.value}_")
    lines.append("\n_Reply with another order reference to check a different order._")
    return "\n".join(lines)


def handle_marketplace_step(
    session: MarketplaceSession, message: str, db: Session
) -> tuple[str, list[str] | None]:
    """
    ALWAYS returns a (text, items) tuple. Every return path in this
    function must follow this contract — router.py unconditionally does
    `text, items = handle_marketplace_step(...)`, so a bare string return
    here will crash it with a ValueError.

    `items` is a list of tappable option labels when the reply should
    render as a List Picker (never more than 10 — see pagination helpers
    above); `items` is None when it's plain text.
    """
    categories = get_all_categories(db)
    if not categories:
        return (
            "Sorry, no categories are available right now. Please try again later.",
            None,
        )

    # First-ever message from this phone number, or session was reset
    if session.pending_action is not None and session.selected_business_id is None:
        is_stale = (datetime.now(timezone.utc) - session.updated_at) > timedelta(
            minutes=SESSION_TIMEOUT_MINUTES
        )
        if is_stale:
            session.pending_action = None
            session.selected_business_type = None
            session.list_offset = 0
            db.commit()

    if session.pending_action is None and session.selected_business_id is None:
        session.pending_action = "select_need"
        session.list_offset = 0
        db.commit()
        titled = [c.title() for c in categories]
        return (
            " Welcome to AISHA Marketplace!\nWhat are you looking for today?",
            _menu_items_for_offset(titled, 0),
        )

    if session.pending_action == "select_need":
        titled_categories = [c.title() for c in categories]
        choice, next_page = _resolve_paginated_choice(
            message, titled_categories, session, db
        )

        if next_page is not None:
            return "What are you looking for today?", next_page

        if choice is None:
            return "Sorry, please reply with a number from the list above.", None

        matched_category = next(c for c in categories if c.title() == choice)
        businesses = get_businesses_by_category(db, matched_category)

        if not businesses:
            return (
                "No stores found for that category right now. Please choose another.",
                None,
            )

        session.selected_business_type = matched_category
        session.pending_action = "select_business"
        session.list_offset = 0
        db.commit()
        # .strip() here for the same reason as get_all_categories() — a
        # business_name saved with stray whitespace would otherwise render
        # clean in WhatsApp's UI while silently failing to match on reply.
        store_names = [b.business_name.strip() for b in businesses]
        return "Here are stores for you:", _menu_items_for_offset(store_names, 0)

    if session.pending_action == "select_business":
        businesses = get_businesses_by_category(db, session.selected_business_type)
        store_names = [b.business_name.strip() for b in businesses]
        choice, next_page = _resolve_paginated_choice(message, store_names, session, db)

        if next_page is not None:
            return "Here are stores for you:", next_page

        if choice is None:
            return "Sorry, please reply with a number from the list above.", None

        chosen = next(b for b in businesses if b.business_name.strip() == choice)
        session.selected_business_id = chosen.id
        session.pending_action = "awaiting_product_choice"
        session.list_offset = 0
        db.commit()
        # Ensure a cart exists for this store the moment they enter it,
        # so downstream "add to cart" logic never has to create-or-fetch.
        get_or_create_cart(session.phone_number, chosen.id, db)

        products = get_products_for_business_category(
            db, chosen.id, session.selected_business_type
        )
        has_photos = any(p.image_url for p in products)

        if not products:
            # No stock at all — nothing for _send_product_photos to send
            # either, so this is the only message the customer gets.
            welcome = (
                f"Welcome to {chosen.business_name}! "
                "We don't have items in that category right now — want to see "
                "something else? Reply 'menu' to browse other stores."
            )
        elif has_photos:
            # router.py's _send_product_photos() sends each product's photo
            # (with name/price/size already in its caption) right after this
            # text — so this intro deliberately does NOT repeat that detail;
            # duplicating it here was the original bug being fixed.
            product_names = ", ".join(p.name for p in products[:5])
            welcome = (
                f"Welcome to {chosen.business_name}! Here's what we have in "
                f"{session.selected_business_type}: {product_names} 👇\n\n"
                "Reply with a product name to see more and order.\n\n"
                "_Tip: reply 'menu' anytime to browse other stores._"
            )
        else:
            # No product in this category has a photo — the short teaser
            # above would point the customer at photos that never arrive.
            # Fall back to the full text list so they still get something
            # to act on, same defensive-fallback pattern used elsewhere
            # in this project (e.g. send_browse_more_prompt's text fallback).
            product_text = format_product_list_for_business(
                db, chosen.id, session.selected_business_type
            )
            welcome = (
                f"Welcome to {chosen.business_name}! Here's what we have in "
                f"{session.selected_business_type}:\n\n"
                + product_text
                + "\n\n_Tip: reply 'menu' anytime to browse other stores._"
            )
        return welcome, None

    if session.pending_action == "awaiting_product_choice":
        product = resolve_product_choice(
            session.selected_business_id, session.selected_business_type, message, db
        )
        if product is None:
            return (
                "Sorry, I didn't recognize that product. Please reply with a "
                "product name from the list above, or 'menu' to start over.",
                None,
            )

        session.selected_product_id = product.id

        if product.variant_label and product.variant_options:
            session.pending_action = "awaiting_size"
            db.commit()
            sizes = _parse_sizes(product.variant_options)
            prompt = (
                f"Great choice! What {product.variant_label.lower()} would you "
                f"like for *{product.name}*?"
            )
            # Sizes are customer-defined free text (variant_options) — in the
            # rare case a business enters more than 10, truncate defensively
            # rather than violate the List Picker's hard cap.
            return prompt, sizes[:10]

        session.pending_action = "awaiting_quantity"
        db.commit()
        return f"Great choice! How many *{product.name}* would you like?", None

    if session.pending_action == "awaiting_size":
        product = db.query(Product).get(session.selected_product_id)
        if product is None:
            # Product was deleted/deactivated mid-flow — don't trap the
            # customer against a choice that no longer exists.
            session.pending_action = "awaiting_product_choice"
            session.selected_product_id = None
            db.commit()
            return (
                "Sorry, that product is no longer available. Please choose another.",
                None,
            )

        size = resolve_size_choice(message, product.variant_options)
        if size is None:
            sizes = _parse_sizes(product.variant_options)
            return (
                "Sorry, please choose a valid option:\n" + _format_numbered_list(sizes),
                sizes[:10],
            )

        session.selected_size = size
        session.pending_action = "awaiting_quantity"
        db.commit()
        return f"Got it — {size}. How many would you like?", None

    if session.pending_action == "awaiting_quantity":
        qty = parse_quantity(message)
        if qty is None:
            return (
                "Please reply with a number (e.g. 1, 2, 3) for how many you'd like.",
                None,
            )

        product = db.query(Product).get(session.selected_product_id)
        if product is None:
            session.pending_action = "awaiting_product_choice"
            session.selected_product_id = None
            session.selected_size = None
            db.commit()
            return (
                "Sorry, that product is no longer available. Please choose another.",
                None,
            )

        cart = get_or_create_cart(
            session.phone_number, session.selected_business_id, db
        )
        add_item_to_cart(cart, product, session.selected_size, qty, db)

        session.selected_product_id = None
        session.selected_size = None
        session.pending_action = "post_add"
        db.commit()

        return (
            f"Added {qty}x {product.name} to your cart! 🛒\n\n"
            + format_cart_summary(cart)
            + "\n\nReply 'add more' to keep shopping, or 'checkout' to complete your order.",
            None,
        )

    if session.pending_action == "post_add":
        if is_checkout_command(message):
            cart = get_or_create_cart(
                session.phone_number, session.selected_business_id, db
            )
            if not cart.items:
                return "Your cart is empty — add something first!", None
            session.pending_action = "awaiting_checkout_info"
            db.commit()
            return (
                format_cart_summary(cart)
                + "\n\nTo complete your order, please reply with your name and "
                "phone number (e.g. 'John Doe 0712345678').",
                None,
            )

        # Anything else here is treated as "add more" — resend the product
        # list for the store they're already in rather than require an
        # exact keyword match.
        session.pending_action = "awaiting_product_choice"
        db.commit()
        product_text = format_product_list_for_business(
            db, session.selected_business_id, session.selected_business_type
        )
        return product_text, None

    if session.pending_action == "awaiting_checkout_info":
        cart = get_or_create_cart(
            session.phone_number, session.selected_business_id, db
        )
        if not cart.items:
            session.pending_action = "post_add"
            db.commit()
            return "Your cart is empty — nothing to check out.", None

        name, contact = parse_name_and_contact(message)
        if not contact:
            contact = (
                session.phone_number
            )  # always known — it's the channel they messaged on

        business = db.query(User).get(session.selected_business_id)
        customer = (
            db.query(Customer)
            .filter(
                Customer.phone_number == session.phone_number,
                Customer.business_id == session.selected_business_id,
            )
            .first()
        )
        if customer is None:
            # Defensive — the webhook's normal get-or-create should already
            # have made this row, but don't let a missing Customer block checkout.
            customer = Customer(
                phone_number=session.phone_number,
                business_id=session.selected_business_id,
                name=name,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

        # summary_before_clear = format_cart_summary(cart)
        orders = create_orders_from_cart(cart, business, customer, name, contact, db)

        cart.items = []
        db.commit()

        session.pending_action = "awaiting_product_choice"
        db.commit()

        order_ref = str(orders[0].order_group_id)[:8] if orders else "N/A"

        items_lines = [
            f"- {o.quantity}x {o.snapshot_product_name} - Ksh {o.total_amount:.2f} - _{o.status.value}_"
            for o in orders
        ]
        total = sum(o.total_amount for o in orders)
        return (
            f"Thank you, {name}! Your order has been placed ✅\n"
            f"Order reference: #{order_ref}\n\n"
            + "\n".join(items_lines)
            + f"\n\nTotal: Ksh {total:.2f}\n\n"
            "_Each item is tracked separately, so status may update at "
            "different times — just quote your order reference if you "
            "check in._\n\n"
            "_Reply 'menu' to browse other stores, or name a product to keep shopping here._",
            None,
        )

        return welcome, None

    # Defensive fallback — should be unreachable given the branches above,
    # but guarantees the tuple contract is never broken even if
    # pending_action somehow holds an unexpected value.
    return "Sorry, something went wrong. Please reply 'menu' to start over.", None


def format_product_list_for_business(
    db: Session,
    business_id: uuid.UUID,
    category_name: str,
) -> str:
    """Public wrapper so router.py can resend the product list (e.g. after
    an 'Add More' tap) without duplicating _format_product_list's logic."""
    products = get_products_for_business_category(db, business_id, category_name)
    return _format_product_list(products)


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

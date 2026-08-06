import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.models import (
    Cart,
    Category,
    Customer,
    MarketplaceSession,
    Order,
    Product,
    User,
)
from app.utils import to_e164
from app.webhook.client import send_text_message

# How long a customer's mid-flow state (e.g. "awaiting_size") stays valid
# before we treat it as abandoned and reset them to the top-level menu.
SESSION_TIMEOUT_HOURS = 24

SWITCH_KEYWORDS = {"switch", "switch store", "change store", "menu", "other shops"}
CHECKOUT_KEYWORDS = {"checkout", "check out", "done", "complete order", "finish order"}
STATUS_KEYWORDS = {"status","order status","my order","track order","track my order"}
PHOTO_KEYWORDS = {
    "photo", "picture", "pic", "image", "see it", "show me",
    "how does it look", "picha", "onyesha picha",
}

# Explicit human-handover requests. Checked BEFORE any deterministic
# marketplace state (select_need/select_business in handle_marketplace_step,
# and every awaiting_* branch in webhook/router.py) so a customer mid-flow
# is never trapped by state-specific parsing when they explicitly ask to
# speak with a person. Deliberately narrower than the LLM's own handover
# criteria (no complaint/scam wording here) to keep false positives low
# inside tight, numeric/size-driven deterministic flows.
HUMAN_HANDOVER_KEYWORDS = {
    "human", "human agent", "a human", "real person", "real human",
    "talk to a human", "speak to a human", "talk to human", "speak to human",
    "talk to someone", "speak to someone", "talk to a person", "speak to a person",
    "talk to the owner", "speak to the owner", "talk to owner", "speak to owner",
    "the owner", "business owner", "manager", "customer service", "customer care",
    "representative", "an agent", "human agent please", "connect me with", "connect me to",
    # Kiswahili
    "binadamu", "wakala", "meneja", "mmiliki", "ongea na mtu",
    "ongea na binadamu", "mtu halisi",
}

NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

ORDER_STATUS_LABELS = {
    "pending": "Order received, awaiting confirmation",
    "paid": "Payment confirmed, preparing your order",
    "shipping": "On its way to you",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

BUSINESS_QUESTION_KEYWORDS = (
    # stock / variant availability
    "do you have", "is there a", "any other color", "any other colour",
    "different color", "different colour", "any in", "got any", "any chance of",
    # store location
    "where is", "where are you", "your location", "store located", "located",
    # delivery / shipping coverage
    "where do you deliver", "do you deliver", "deliver to", "delivery area",
    "where do you guys deliver", "shipping to",
)


def friendly_status(status_value: str) -> str:
    return ORDER_STATUS_LABELS.get(status_value, status_value.replace("_", " ").title())

PAGE_SIZE = 9
MORE_OPTIONS_LABEL = "More options"


def _get_offset(session: MarketplaceSession) -> int:
    return session.list_offset or 0


def _menu_items_for_offset(all_items: list[str], offset: int) -> list[str]:
    page = all_items[offset : offset + PAGE_SIZE]
    has_more = (offset + PAGE_SIZE) < len(all_items)
    return page + [MORE_OPTIONS_LABEL] if has_more else page


def _resolve_paginated_choice(
    message: str, all_items: list[str], session: MarketplaceSession, db: Session
) -> tuple[str | None, list[str] | None]:
    offset = _get_offset(session)
    display_items = _menu_items_for_offset(all_items, offset)
    choice = _resolve_choice(message, display_items)

    if choice == MORE_OPTIONS_LABEL:
        next_offset = offset + PAGE_SIZE
        if next_offset >= len(all_items):
            next_offset = 0
        session.list_offset = next_offset
        db.commit()
        return None, _menu_items_for_offset(all_items, next_offset)

    return choice, None

def is_photo_request(message: str) -> bool:
    text = message.strip().lower()
    return any(kw in text for kw in PHOTO_KEYWORDS)


def is_human_handover_request(message: str) -> bool:
    """Deterministic, keyword-based check for an explicit request to speak
    with a human/agent/owner/manager. Unlike detect_handover() in
    app.ai.service (which only inspects the LLM's own [HANDOVER_REQUIRED]
    tag from inside the AI Q&A path), this runs BEFORE any marketplace
    deterministic state is allowed to swallow the message with its own
    state-specific fallback reply — see webhook/router.py's call sites."""
    text = message.strip().lower()
    return any(kw in text for kw in HUMAN_HANDOVER_KEYWORDS)


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
    return message.strip().lower() in SWITCH_KEYWORDS


def is_checkout_command(message: str) -> bool:
    return message.strip().lower() in CHECKOUT_KEYWORDS


def is_status_command(message: str) -> bool:
    return message.strip().lower() in STATUS_KEYWORDS


def reset_to_menu(session: MarketplaceSession, db: Session) -> None:
    session.selected_business_id = None
    session.selected_business_type = None
    session.selected_product_id = None
    session.selected_size = None
    session.pending_action = None
    session.list_offset = 0
    db.commit()


def reset_after_checkout(session: MarketplaceSession, db: Session) -> None:
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
    rows = (
        db.query(Category.name)
        .filter(Category.is_active)
        .distinct()
        .order_by(Category.name)
        .all()
    )
    return [r[0].strip() for r in rows if r[0] and r[0].strip()]


def get_businesses_by_category(db: Session, category_name: str) -> list[User]:
    # Uses a correlated EXISTS subquery instead of `join(...).distinct()` so
    # a business with multiple matching Category rows is still returned
    # only once, without needing SELECT DISTINCT on the full User row.
    # `users.handover_notifications` is a JSON column, and Postgres has no
    # equality operator for `json` (only `jsonb`), so `SELECT DISTINCT
    # users.*` fails with `UndefinedFunction: could not identify an
    # equality operator for type json`.
    category_match = (
        db.query(Category.id)
        .filter(
            Category.business_id == User.id,
            Category.name == category_name,
            Category.is_active,
        )
        .exists()
    )
    return (
        db.query(User)
        .filter(User.is_active, category_match)
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
    return "\n".join(f"{i + 1} {label_fn(item)}" for i, item in enumerate(items))


def _parse_sizes(variant_options: str) -> list[str]:
    if not variant_options:
        return []
    return [s.strip() for s in variant_options.split(",") if s.strip()]


def resolve_size_choice(text: str, variant_options: str) -> str | None:
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
    text_clean = text.strip()
    if text_clean.isdigit():
        qty = int(text_clean)
        if 1 <= qty <= 100:
            return qty
    return None


def add_item_to_cart(
    cart: Cart, product: Product, size: str | None, qty: int, db: Session
) -> None:
    items = list(cart.items or [])
    
    for item in items:
        if item["product_id"] == str(product.id) and item.get("size") == size:
            item["qty"] += qty
            cart.items = items
            db.commit()
            return
        
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
    match = re.search(r"\b[0-9a-fA-F]{8}\b", message)
    return match.group(0) if match else None


def get_orders_by_reference(ref: str, phone_number: str, db: Session) -> list[Order]:
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
        return [latest]
    return db.query(Order).filter(Order.order_group_id == latest.order_group_id).all()


def get_latest_orders_for_business(
    phone_number: str, business_id: uuid.UUID, db: Session
) -> list[Order]:
    latest = (
        db.query(Order)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(Customer.phone_number == phone_number, Order.business_id == business_id)
        .order_by(Order.created_at.desc())
        .first()
    )
    if not latest:
        return []
    if not latest.order_group_id:
        return [latest]
    return db.query(Order).filter(Order.order_group_id == latest.order_group_id).all()

def is_business_question(message: str) -> bool:
    """Catches questions only the business itself can answer — stock/variant
    availability, store location, delivery coverage — so they route to a
    human handover instead of the generic 'didn't recognize that' fallback.
    Deliberately keyword-based, not AI-routed: keeps this state fully
    deterministic like every other awaiting_* branch (see
    _send_fallback_reply's docstring above), at the cost of needing this
    list extended by hand as new phrasings turn up in real conversations."""
    text = message.strip().lower()
    return any(kw in text for kw in BUSINESS_QUESTION_KEYWORDS)


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
        lines.append(f"- {o.quantity}x {o.snapshot_product_name} — _{friendly_status(o.status.value)}_")
    lines.append("\n_Reply with another order reference to check a different order._")
    return "\n".join(lines)

def _send_status_notification(order: Order, message: str) -> None:
    """Shared phone validation + send step for every order-status
    notification (paid, shipped, delivered, ...). Centralizing this means
    a phone-handling fix (like the to_e164 normalization) only has to
    happen in one place, not once per notify_* function."""
    phone = to_e164(order.snapshot_customer_phone) if order.snapshot_customer_phone else None
    if not phone:
        print(f"[order_notification] Skipped — invalid/missing phone for order {order.id}: {order.snapshot_customer_phone!r}")
        return
    send_text_message(to_phone=phone, message=message)

def notify_shipping(order: Order, business: User, db: Session) -> None:
    location_line = (
        f"\nYou can collect it at: {business.delivery_location}"
        if business.delivery_location else ""
    )
    message = (
        f"📦 Update: *{order.snapshot_product_name}* from your order "
        f"#{str(order.order_group_id or order.id)[:8]} with {business.business_name} "
        f"is now *{friendly_status(order.status.value)}*."
        f"{location_line}\n\n"
        "_Reply 'status' anytime to see all your items._"
    )
    _send_status_notification(order, message)

def notify_payment_received(order: Order, business: User, db: Session) -> None:
    """Fires the moment an item moves into PAID — reassures the customer
    their money was received before anything ships, which matters most
    for M-Pesa-style payments where confirmation isn't always instant
    or visible on the customer's end."""
    message = (
        f"✅ Payment received for *{order.snapshot_product_name}* from your order "
        f"#{str(order.order_group_id or order.id)[:8]} with {business.business_name}. "
        "We're preparing it now!\n\n"
        "_Reply 'status' anytime to see all your items._"
    )
    _send_status_notification(order, message)


def notify_delivered(order: Order, business: User, db: Session) -> None:
    """Delivered here means 'ready at the business's collection point',
    matching the pickup model notify_shipping already assumes
    (business.delivery_location) — not a door-to-door delivery address.
    Reword the location line to 'delivered to' if your businesses are
    actually doing doorstep drop-offs instead of pickup points."""
    location_line = (
        f"\nCollected from / delivered to: {business.delivery_location}"
        if business.delivery_location else ""
    )
    message = (
        f"🎉 *{order.snapshot_product_name}* from your order "
        f"#{str(order.order_group_id or order.id)[:8]} with {business.business_name} "
        f"has been *delivered*!{location_line}\n\n"
        "Thanks for shopping with us — reply 'menu' anytime to shop again."
    )
    _send_status_notification(order, message)
    
def notify_cancelled(order: Order, business: User, db: Session, was_paid: bool) -> None:
    """was_paid reflects the item's status *before* cancellation — passed
    in by the caller rather than inferred here, since by the time this
    runs `order.status` is already CANCELLED and the prior state is only
    known to whoever called update_order_status. If payment had already
    gone through (PAID or SHIPPED before cancelling), the customer is
    owed money back and needs to be told that explicitly — a bare
    'cancelled' message with no mention of their money would be
    confusing and could look like the business just kept it."""
    refund_line = (
        "\n\nSince payment was already received for this item, we'll be "
        "in touch shortly about your refund."
        if was_paid else ""
    )
    message = (
        f"❌ Update: *{order.snapshot_product_name}* from your order "
        f"#{str(order.order_group_id or order.id)[:8]} with {business.business_name} "
        f"has been *cancelled*.{refund_line}\n\n"
        "_Reply 'status' anytime to see all your items, or 'menu' to shop again._"
    )
    _send_status_notification(order, message)
    
    

def handle_marketplace_step(
    session: MarketplaceSession, message: str, db: Session
) -> tuple[str, list[str] | None]:
    categories = get_all_categories(db)
    if not categories:
        return (
            "Sorry, no categories are available right now. Please try again later.",
            None,
        )

    if session.pending_action is not None and session.selected_business_id is None:
        is_stale = (datetime.now(timezone.utc) - session.updated_at) > timedelta(
            hours=SESSION_TIMEOUT_HOURS
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
        cart = get_or_create_cart(session.phone_number, chosen.id, db)

        products = get_products_for_business_category(
            db, chosen.id, session.selected_business_type
        )
        has_photos = any(p.image_url for p in products)

        if not products:
            welcome = (
                f"Welcome to {chosen.business_name}! "
                "We don't have items in that category right now — want to see "
                "something else? Reply 'menu' to browse other stores."
            )
        elif has_photos:
            # Was previously products[:5]-truncated in the welcome TEXT
            # (separate from the 5-photo cap in router.py's
            # _send_product_photos, which is intentional and unrelated).
            # That silently hid any product past the 5th — a category with
            # 8 hair clip variants only ever mentioned 5 by name, so a
            # customer could never ask for the other 3 by name since they
            # were never told those names existed. Now reuses the same
            # full-listing helper the other two welcome branches already
            # use, so every product in the category is named regardless
            # of how many photos get auto-sent alongside it.
            product_text = format_product_list_for_business(
                db, chosen.id, session.selected_business_type
            )
            welcome = (
                f"Welcome to {chosen.business_name}! Here's what we have in "
                f"{session.selected_business_type}:\n\n"
                + product_text
                + "\n\n_Tip: reply 'menu' anytime to browse other stores._"
            )
        else:
            product_text = format_product_list_for_business(
                db, chosen.id, session.selected_business_type
            )
            welcome = (
                f"Welcome to {chosen.business_name}! Here's what we have in "
                f"{session.selected_business_type}:\n\n"
                + product_text
                + "\n\n_Tip: reply 'menu' anytime to browse other stores._"
            )
        if cart.items:
            welcome += (
                f"\n\n *You still have items in your cart here:*\n"
                f"{format_cart_summary(cart)}\n\n"
                "Reply 'checkout' anytime to complete this order."
            )
        return welcome, None

    if session.pending_action == "awaiting_product_choice":
        product = resolve_product_choice(
            session.selected_business_id, session.selected_business_type, message, db
        )
        if product is None:
            return (
                (
                    "Sorry, I didn't recognize that product. Please reply with a "
                    "product name from the list above, or 'menu' to start over."
                ),
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
            return prompt, sizes[:10]

        session.pending_action = "awaiting_quantity"
        db.commit()
        return f"Great choice! How many *{product.name}* would you like?", None

    if session.pending_action == "awaiting_size":
        product = db.query(Product).get(session.selected_product_id)
        if product is None:
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

        session.last_product_id = product.id
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
            )

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
            customer = Customer(
                phone_number=session.phone_number,
                business_id=session.selected_business_id,
                name=name,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

        orders = create_orders_from_cart(cart, business, customer, name, contact, db)

        cart.items = []
        db.commit()

        session.pending_action = "awaiting_product_choice"
        db.commit()

        order_ref = str(orders[0].order_group_id)[:8] if orders else "N/A"

        items_lines = [
            f"- {o.quantity}x {o.snapshot_product_name} - Ksh {o.total_amount:.2f} - _{friendly_status(o.status.value)}_"
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


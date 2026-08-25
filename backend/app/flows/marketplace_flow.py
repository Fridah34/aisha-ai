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
#
# Only ever consulted by handle_marketplace_step's pre-store branch. It is NOT
# the general session TTL — see MARKETPLACE_SESSION_TTL below, which is the one
# that actually protects customers already inside a store.
SESSION_TIMEOUT_HOURS = 24

# Inactivity window after which get_or_create_marketplace_session resets a
# customer to the top-level menu.
#
# Why this exists: handle_marketplace_step's own staleness check (above) is
# gated on `selected_business_id is None`, so it can only ever fire for a
# customer who has NOT entered a store. Once selected_business_id is set,
# nothing expired the session, and message_processor short-circuits
# handle_marketplace_step entirely for those customers. The observed effect was
# sessions pinned at pending_action='awaiting_product_choice' with
# selected_product_id=NULL for days: every incoming message got interpreted as
# a product choice first, and the customer's only escape was typing one of
# SWITCH_KEYWORDS exactly.
#
# Measured against MarketplaceSession.updated_at, which
# get_or_create_marketplace_session touches on every inbound message. That
# makes this a true "15 minutes since the customer last said anything" window
# rather than "15 minutes since the state last changed" — without the touch, a
# customer chatting to the LLM (a path that mutates no session columns) would
# get yanked back to the menu mid-conversation.
MARKETPLACE_SESSION_TTL = timedelta(minutes=15)

# Hard ceiling on any free-text field we accept off a WhatsApp payload before it
# reaches a query, a regex or a DB column. WhatsApp itself caps bodies around
# 4096 chars; anything longer is malformed or hostile. Applied by
# sanitize_incoming_text() below.
MAX_INBOUND_TEXT_CHARS = 1000

# Longest numeric run we'll even try to read as a menu selection. A list never
# has more than a few dozen entries, so a 6-digit cap is generous — it exists
# so a pathological "9" * 100000 payload can't reach int().
MAX_MENU_SELECTION_DIGITS = 6

# How long a "last viewed product" guess (see _resolve_photo_target below)
# stays trustworthy before we treat it as stale and ignore it. Defined here
# — not in message_processor.py, which only *calls* _resolve_photo_target —
# since this is the module that actually uses it. message_processor.py
# imports it from here so there's a single source of truth instead of two
# constants that can silently drift apart.
STALE_PHOTO_WINDOW = timedelta(hours=24)

SWITCH_KEYWORDS = {"switch", "switch store", "change store", "menu", "other shops"}
CHECKOUT_KEYWORDS = {"checkout", "check out", "done", "complete order", "finish order"}
STATUS_KEYWORDS = {
    "status",
    "order status",
    "my order",
    "track order",
    "track my order",
}
PHOTO_KEYWORDS = {
    "photo",
    "picture",
    "pic",
    "image",
    "see it",
    "show me",
    "how does it look",
    "picha",
    "onyesha picha",
}

# Explicit human-handover requests. Checked BEFORE any deterministic
# marketplace state (select_need/select_business in handle_marketplace_step,
# and every awaiting_* branch in webhook/router.py) so a customer mid-flow
# is never trapped by state-specific parsing when they explicitly ask to
# speak with a person. Deliberately narrower than the LLM's own handover
# criteria (no complaint/scam wording here) to keep false positives low
# inside tight, numeric/size-driven deterministic flows.
HUMAN_HANDOVER_KEYWORDS = {
    "human",
    "human agent",
    "a human",
    "real person",
    "real human",
    "talk to a human",
    "speak to a human",
    "talk to human",
    "speak to human",
    "talk to someone",
    "speak to someone",
    "talk to a person",
    "speak to a person",
    "talk to the owner",
    "speak to the owner",
    "talk to owner",
    "speak to owner",
    "the owner",
    "business owner",
    "manager",
    "customer service",
    "customer care",
    "representative",
    "an agent",
    "human agent please",
    "connect me with",
    "connect me to",
    # Kiswahili
    "binadamu",
    "wakala",
    "meneja",
    "mmiliki",
    "ongea na mtu",
    "ongea na binadamu",
    "mtu halisi",
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
    "do you have",
    "is there a",
    "any other color",
    "any other colour",
    "different color",
    "different colour",
    "any in",
    "got any",
    "any chance of",
    # store location
    "where is",
    "where are you",
    "your location",
    "store located",
    "located",
    # delivery / shipping coverage
    "where do you deliver",
    "do you deliver",
    "deliver to",
    "delivery area",
    "where do you guys deliver",
    "shipping to",
    # hours of operation
    "what time",
    "opening hours",
    "operating hours",
    "business hours",
    "closing time",
    "open until",
    "still open",
    "are you open",
    "when do you open",
    "when do you close",
    "what time do you open",
    "what time do you close",
    "your hours",
)

QUESTION_STARTERS = (
    "do you",
    "does it",
    "does he",
    "does she",
    "is there",
    "is it",
    "is that",
    "is this",
    "are you",
    "are there",
    "can i",
    "can you",
    "could i",
    "could you",
    "will you",
    "would you",
    "what",
    "where",
    "when",
    "why",
    "how",
    "which",
    "who",
)


def looks_like_question(message: str) -> bool:
    """Loose, catch-all 'this is probably a question, not a menu
    selection' check — deliberately broader than is_business_question().

    SAFE TO USE ONLY once a business is already selected (i.e. from
    router.py's post-selection states: awaiting_product_choice,
    awaiting_photo_choice, awaiting_size, awaiting_quantity,
    awaiting_cart_action, awaiting_checkout_info). Before a store is
    picked (select_need / select_business in this file), the stricter
    is_business_question() keyword list is what protects against
    answering from the wrong business's catalog — this function must not
    be used there.

    Exists because BUSINESS_QUESTION_KEYWORDS will never fully enumerate
    every real phrasing a customer uses ("you guys open?", "still open
    today?", "opening time?"...). This catches those by shape ("starts
    with a question word", "ends with a question mark") rather than by
    exact phrase, at the cost of occasionally sending an AI call for a
    message that turns out to be junk — a far cheaper failure than
    silently telling a real customer 'sorry, I didn't understand'.
    """
    text = message.strip().lower()
    if not text:
        return False
    if text.endswith("?"):
        return True
    return text.startswith(QUESTION_STARTERS)


def is_business_question(message: str) -> bool:
    """Catches questions only the business itself can answer — stock/variant
    availability, store location, delivery coverage — so they route to a
    human handover instead of the generic 'didn't recognize that' fallback.
    Deliberately keyword-based, not AI-routed: keeps this state fully
    deterministic like every other awaiting_* branch (see
    _send_fallback_reply's docstring above), at the cost of needing this
    list extended by hand as new phrasings turn up in real conversations.

    Used on its own (without looks_like_question) in select_need /
    select_business, where no business is selected yet and a wrong guess
    here has no safe fallback. Used together with looks_like_question()
    everywhere else, in router.py, once a business_id is locked in."""
    text = message.strip().lower()
    return any(kw in text for kw in BUSINESS_QUESTION_KEYWORDS)


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


def sanitize_incoming_text(raw: str | None) -> str:
    """Normalises any free-text field taken off a WhatsApp webhook payload
    before it reaches a regex, a DB query or a DB column.

    Deliberately conservative — this is a normaliser, not a content filter.
    Prompt-injection defence lives in app.knowledge_base.security
    (sanitize_untrusted_text / the CTX fence), and product/category matching
    is exact-match against DB values, so the job here is only to stop
    malformed or oversized input from reaching the layers below:

      - Strips C0/C1 control characters, which can corrupt log output and
        confuse the numeric-selection parsers, while keeping \\n and \\t.
      - Collapses the runaway whitespace WhatsApp forwards sometimes carry.
      - Truncates to MAX_INBOUND_TEXT_CHARS so an oversized body can't blow a
        String(n) column on insert (snapshot_customer_name is String(120))
        or make the catch-all regexes in this module pathological.

    Returns "" for None so callers never have to guard for it.
    """
    if not raw:
        return ""

    # Keep \n and \t; drop every other control char including the C1 range.
    cleaned = "".join(
        ch
        for ch in raw
        if ch in ("\n", "\t") or (ord(ch) >= 32 and not (127 <= ord(ch) <= 159))
    )
    # Collapse runs of 3+ blank lines and any run of spaces/tabs.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) > MAX_INBOUND_TEXT_CHARS:
        cleaned = cleaned[:MAX_INBOUND_TEXT_CHARS].rstrip()

    return cleaned


def get_or_create_marketplace_session(
    phone_number: str, db: Session
) -> MarketplaceSession:
    """Fetches (or creates) the customer's marketplace session and enforces
    MARKETPLACE_SESSION_TTL.

    The TTL check happens here rather than in handle_marketplace_step because
    this is the single chokepoint every inbound message passes through —
    message_processor calls it before any branching, including the branches
    that never reach handle_marketplace_step at all. That is precisely the gap
    that let 'awaiting_product_choice' persist for days.
    """
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

    now = datetime.now(timezone.utc)

    # updated_at is server_default=now() / onupdate=now(), so it should always
    # be populated — but a row inserted by a raw SQL fixture or an older
    # migration might not be. Treat a missing timestamp as "not stale" so a
    # data quirk can never wipe a live session.
    last_seen = session.updated_at
    has_state = (
        session.pending_action is not None or session.selected_business_id is not None
    )

    if (
        last_seen is not None
        and has_state
        and (now - last_seen) > MARKETPLACE_SESSION_TTL
    ):
        idle_minutes = int((now - last_seen).total_seconds() // 60)
        print(
            f"[Marketplace] Session for {phone_number} idle {idle_minutes}m "
            f"(action={session.pending_action!r}, business={session.selected_business_id}) "
            f"— resetting to menu"
        )
        reset_to_menu(session, db)
        return session

    # Touch updated_at on every message so the TTL measures customer
    # inactivity, not time-since-last-state-change. Without this, the pure-LLM
    # Q&A path (which mutates no session columns) would let updated_at go stale
    # under an actively chatting customer and reset them mid-conversation.
    #
    # Assigned explicitly rather than relying on onupdate= because SQLAlchemy
    # only fires onupdate when some other column is actually dirty.
    session.updated_at = now
    db.commit()

    return session


def is_switch_command(message: str) -> bool:
    return message.strip().lower() in SWITCH_KEYWORDS


def is_checkout_command(message: str) -> bool:
    return message.strip().lower() in CHECKOUT_KEYWORDS


def is_status_command(message: str) -> bool:
    return message.strip().lower() in STATUS_KEYWORDS


def reset_to_menu(session: MarketplaceSession, db: Session) -> None:
    """Returns the customer to the top-level marketplace menu.

    Clears last_product_id/last_product_at as well: that pair is the "photo
    request with no named product" fallback, and it is scoped to one store.
    Carrying it across a store switch is how a photo request in the new store
    could be answered with the previous store's product.
    """
    session.selected_business_id = None
    session.selected_business_type = None
    session.selected_category = None
    session.selected_product_id = None
    session.selected_size = None
    session.pending_action = None
    session.list_offset = 0
    session.last_product_id = None
    session.last_product_at = None
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


def get_category_id_for_business(
    db: Session,
    business_id: uuid.UUID,
    category_name: str | None,
) -> uuid.UUID | None:
    """Resolves (business_id, category_name) -> category_id.

    Pulled out as its own function rather than left inline because two
    separate call sites now need this exact lookup: get_products_for_business_category
    below, and message_processor.py's _resolve_photo_target (which needs
    the id to check whether a candidate "last viewed product" fallback
    actually belongs to the category the customer is currently browsing,
    rather than trusting a stale id from an earlier, unrelated shopping
    session). One function means both stay in sync if the lookup logic
    (e.g. is_active filtering) ever changes.

    Returns None for a missing business_id or a blank category name rather than
    emitting `WHERE name IS NULL`, which would silently match nothing and read
    as "category doesn't exist" instead of "no category was asked for".
    """
    if not business_id or not category_name or not str(category_name).strip():
        return None

    category = (
        db.query(Category)
        .filter(
            Category.business_id == business_id,
            Category.name == category_name,
            Category.is_active,
        )
        .first()
    )
    return category.id if category else None


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
        .order_by(Product.name)
        .all()
    )


def get_products_for_business(db: Session, business_id: uuid.UUID) -> list[Product]:
    """Every purchasable product for one business, regardless of category.

    The category-agnostic path. Needed because a product's category_id is
    nullable, so a product that was never assigned a category is invisible to
    every category-scoped query — it can't be listed, chosen by name, or have
    its photo sent, even though it shows up in the LLM's flat catalog and the
    owner's dashboard. This is also the fallback whenever no category is
    selected on the session.

    Note the flag is `is_available`, not `is_active`: Product uses
    is_available, while User and Category use is_active.
    """
    return (
        db.query(Product)
        .filter(
            Product.business_id == business_id,
            Product.is_available,
        )
        .order_by(Product.name)
        .all()
    )


def get_products_for_business_category(
    db: Session,
    business_id: uuid.UUID,
    category_name: str | None,
) -> list[Product]:
    """Products for (business, category), falling back to the full catalog.

    Two distinct fallbacks, both deliberate:

    1. No category selected — the customer is in the store but hasn't picked a
       category (a fresh session, or the active-business Redis cache reopening
       a store without one). Showing the whole catalog is strictly better than
       showing nothing, which is what returning [] used to do and is a large
       part of "products not displaying for specific businesses".

    2. Category named but unresolvable for THIS business — a stale, renamed or
       deactivated category name on the session. Also falls back to the full
       catalog, and logs, because the customer is standing in a real store.

    An empty-but-real category still correctly yields []: the name resolves, so
    we take the scoped path and simply find no rows. That keeps the "we don't
    have items in that category right now" reply reachable.
    """
    if not business_id:
        return []

    if not category_name or not str(category_name).strip():
        return get_products_for_business(db, business_id)

    category_id = get_category_id_for_business(db, business_id, category_name)
    if not category_id:
        print(
            f"[Marketplace] Category {category_name!r} not found for business "
            f"{business_id} — falling back to full catalog"
        )
        return get_products_for_business(db, business_id)

    return get_products_for_category(db, business_id, category_id)


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
    category_name: str | None,
    message: str,
    db: Session,
) -> Product | None:
    if not business_id:
        return None
    products = get_products_for_business_category(db, business_id, category_name)
    names = [p.name.strip() for p in products]
    choice = _resolve_choice(message, names)
    if choice is not None:
        return next((p for p in products if p.name.strip() == choice), None)

    # FIXED: this used to check `text_clean in p.name.lower()` — i.e.
    # "is the customer's whole message a substring of the product name".
    # That's backwards and near-dead-code: a sentence like "can i see a
    # photo of the crocs?" can never be a substring of "Crocs". What we
    # actually want is the reverse — does the (short) product name appear
    # SOMEWHERE inside the (longer) customer message.
    text_clean = message.strip().lower()
    if text_clean:
        partial_matches = [p for p in products if p.name.strip().lower() in text_clean]
        if len(partial_matches) == 1:
            return partial_matches[0]
        if len(partial_matches) > 1:
            # More than one product's name appears in the message (e.g.
            # message mentions "crocs" and both "Crocs" and "Platform
            # crocs" match). Prefer the longest/most specific name — a
            # message containing "platform crocs" should resolve to
            # "Platform crocs", not fall back to the shorter "Crocs" that
            # also happens to be a substring of it.
            partial_matches.sort(key=lambda p: len(p.name), reverse=True)
            return partial_matches[0]

    return None


def _resolve_photo_target(
    marketplace_session, business_id: uuid.UUID, message_text: str, db: Session
) -> Product | None:
    matched_product = resolve_product_choice(
        business_id=business_id,
        category_name=marketplace_session.selected_category,
        message=message_text,
        db=db,
    )
    if matched_product:
        return matched_product
    if not marketplace_session.last_product_id:
        return None

    # Measured against last_product_at (when the product was actually viewed),
    # not updated_at. updated_at is touched on every inbound message so the
    # session TTL can measure real inactivity, which would make this check
    # permanently true.
    last_seen_product_at = marketplace_session.last_product_at
    if last_seen_product_at is None:
        return None
    if (datetime.now(timezone.utc) - last_seen_product_at) >= STALE_PHOTO_WINDOW:
        return None

    # business_id is part of the filter, not just checked afterwards: this is
    # a customer-supplied id path (last_product_id survives across store
    # switches), so a row from another tenant must never be loaded at all.
    last_product = (
        db.query(Product)
        .filter(
            Product.id == marketplace_session.last_product_id,
            Product.business_id == business_id,
            Product.is_available,
        )
        .first()
    )
    if not last_product:
        return None

    # Only trust the "last viewed product" guess if it actually belongs
    # to the category the customer is currently browsing. Without this,
    # a stale last_product_id from an earlier, unrelated shopping session
    # (different category, possibly hours ago but still inside the 24h
    # freshness window) could get silently substituted for whatever the
    # customer is asking about now — which is exactly what caused Carpet
    # to get matched to a Crocs photo request.
    current_category_id = get_category_id_for_business(
        db, business_id, marketplace_session.selected_category
    )
    if current_category_id and last_product.category_id == current_category_id:
        return last_product
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

    # Size labels like "38 - 40" describe a numeric range. A bare
    # number reply ("38") should resolve to whichever range contains
    # it, since no real customer will retype " 38 -40 " verbatim.
    if text_clean.isdigit():
        num = int(text_clean)
        for s in sizes:
            m = re.match(r"(\d+)\s*-\s*(\d+)", s)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if lo <= num <= hi:
                    return s

    return None


def find_mentioned_alternate_variant(
    message: str,
    business_id: uuid.UUID,
    category_name: str,
    current_product_options: str,
    db: Session,
) -> str | None:
    """Checks whether the customer's message mentions a variant term that
    genuinely exists somewhere in THIS business's catalog for this category
    (color, size, flavor — whatever that business actually uses) but isn't
    available on the CURRENT product.

    Deliberately data-driven, not a hardcoded word list: AISHA serves
    several different business types, each with its own variant vocabulary
    (a boutique's variants are colors/sizes, a food business's might be
    flavors or portion sizes) — a fixed list of English color words would
    only ever be correct for one type of business and would silently claim
    a business "doesn't have" something it never claimed to sell.

    Returns the matched term (as it appears in the catalog) if found, else
    None. None also covers "no match" for a genuinely unrelated message
    (e.g. a business-hours question) — callers should check
    is_business_question() separately for those.
    """
    current_available = {
        s.strip().lower() for s in _parse_sizes(current_product_options)
    }

    products = get_products_for_business_category(db, business_id, category_name)
    catalog_terms: set[str] = set()
    for p in products:
        if p.variant_options:
            catalog_terms.update(
                s.strip().lower() for s in _parse_sizes(p.variant_options)
            )

    text_clean = message.strip().lower()
    for term in catalog_terms:
        if term in current_available:
            continue  # it IS available on this product — not a mismatch
        if re.search(rf"\b{re.escape(term)}\b", text_clean):
            return term

    return None


def parse_quantity(text: str) -> int | None:
    """Reads a 1–100 quantity from a customer reply, or None.

    Length-capped before int() for the same reason as _resolve_choice:
    str.isdigit() is True for a run of any length and Python ints are
    unbounded, so an enormous digit payload would be fully converted before the
    range check discarded it.
    """
    if not text:
        return None
    text_clean = text.strip()
    if text_clean.isdigit() and len(text_clean) <= MAX_MENU_SELECTION_DIGITS:
        qty = int(text_clean)
        if 1 <= qty <= 100:
            return qty
    return None


def add_item_to_cart(
    cart: Cart, product: Product, size: str | None, qty: int, db: Session
) -> None:
    """Adds (or increments) a line in the cart.

    The tenant assertion is the last line of defence for the cart: Cart is
    keyed on (phone_number, business_id) while Product carries its own
    business_id, and nothing in the JSON items blob records which store a line
    came from. If those two ever disagree we would silently build a cart — and
    then Orders — mixing two businesses' products. Refusing loudly beats
    writing corrupt cross-tenant order rows.
    """
    if product.business_id != cart.business_id:
        raise ValueError(
            f"Refusing to add product {product.id} (business "
            f"{product.business_id}) to cart for business {cart.business_id}"
        )

    items = list(cart.items or [])

    for item in items:
        # .get() rather than [] — cart.items is a JSON blob that may predate
        # the current line shape, and a KeyError here would abort the add.
        if item.get("product_id") == str(product.id) and item.get("size") == size:
            item["qty"] = item.get("qty", 0) + qty
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


MAX_CUSTOMER_NAME_CHARS = 80


def parse_name_and_contact(text: str) -> tuple[str, str]:
    """Splits a checkout reply like 'John Doe 0712345678' into (name, phone).

    Both outputs land in Order.snapshot_customer_name / _phone and are echoed
    straight back to the customer, so the name is length-capped and stripped of
    newlines. The columns are unbounded String (no truncation error to avoid),
    but an 800-character "name" pasted into a confirmation message — and into
    the business's dashboard — is its own problem.
    """
    text = sanitize_incoming_text(text)
    if not text:
        return "Customer", ""

    phone_match = re.search(r"(\+?254|0)[71]\d{8}", text)
    contact = phone_match.group(0) if phone_match else ""
    name = text
    if phone_match:
        name = (text[: phone_match.start()] + text[phone_match.end() :]).strip()
    name = re.sub(
        r"\b(my|contact|is|number|phone)\b", "", name, flags=re.IGNORECASE
    ).strip(" ,:-")

    # Collapse to a single line and cap — a checkout name is never multi-line.
    name = " ".join(name.split())
    if len(name) > MAX_CUSTOMER_NAME_CHARS:
        name = name[:MAX_CUSTOMER_NAME_CHARS].rstrip()

    return (name or "Customer"), contact


def create_orders_from_cart(
    cart: Cart, business: User, customer: Customer, name: str, contact: str, db: Session
) -> list[Order]:
    """Turns the cart's JSON items into one Order row per line.

    Every line is re-validated against the DB before it becomes an Order.
    cart.items is a JSON blob that has been sitting in Postgres since the
    customer last shopped, so by checkout time a product may have been
    deleted, pulled from sale, or (if anything upstream ever mismatched)
    belong to a different business entirely. Trusting the blob's product_id
    verbatim is what would let a cross-tenant product_id reach an Order row
    stamped with this business_id.

    Skipped lines are logged and dropped rather than aborting the whole
    checkout — a customer with three good items and one delisted one should
    still get their order.
    """
    group_id = uuid.uuid4()
    orders = []
    for item in cart.items or []:
        raw_product_id = item.get("product_id")
        try:
            product_id = uuid.UUID(str(raw_product_id))
        except (ValueError, AttributeError, TypeError):
            print(
                f"[Checkout] Dropping cart line with malformed product_id {raw_product_id!r}"
            )
            continue

        product = (
            db.query(Product)
            .filter(Product.id == product_id, Product.business_id == business.id)
            .first()
        )
        if product is None:
            print(
                f"[Checkout] Dropping cart line {product_id} — not a product of "
                f"business {business.id}"
            )
            continue

        order = Order(
            order_group_id=group_id,
            customer_id=customer.id,
            product_id=product_id,
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
    """Looks up an order group by its short (8-hex) customer-facing reference.

    Deliberately NOT scoped to one business: a customer who quotes a reference
    should be able to check it whichever store it came from — message_processor
    advertises exactly that ("If you have an order reference from another
    store..."). The tenant boundary that matters here is the CUSTOMER, and it
    is enforced by the Customer.phone_number join: the prefix match can only
    ever reach order groups belonging to this phone number, so a guessed or
    enumerated prefix cannot surface anybody else's order.

    ref is re-validated rather than trusted from the caller — it reaches a LIKE
    pattern, so anything that isn't plain hex is rejected outright instead of
    being interpolated (a bare '%' would otherwise match every one of the
    caller's own orders).
    """
    if not ref:
        return []
    ref_clean = ref.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{4,32}", ref_clean):
        return []

    return (
        db.query(Order)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(
            Customer.phone_number == phone_number,
            func.cast(Order.order_group_id, String).like(f"{ref_clean}%"),
        )
        .order_by(Order.created_at)
        .all()
    )


def _orders_in_group(
    db: Session,
    order_group_id: uuid.UUID,
    *,
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
) -> list[Order]:
    """Expands an order_group_id to its sibling rows, re-scoped.

    An order_group_id is a uuid4 minted per checkout, so in practice every row
    in a group shares one customer and one business. This re-asserts that in
    the WHERE clause anyway: the group id is derived from a row we reached via
    a customer's phone number, and "trust the uuid, skip the tenant predicate"
    is exactly the pattern that turns one bad row into a cross-tenant read.
    """
    return (
        db.query(Order)
        .filter(
            Order.order_group_id == order_group_id,
            Order.customer_id == customer_id,
            Order.business_id == business_id,
        )
        .order_by(Order.created_at)
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
    return _orders_in_group(
        db,
        latest.order_group_id,
        customer_id=latest.customer_id,
        business_id=latest.business_id,
    )


def get_latest_orders_for_business(
    phone_number: str, business_id: uuid.UUID, db: Session
) -> list[Order]:
    if not business_id:
        return []

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
    return _orders_in_group(
        db,
        latest.order_group_id,
        customer_id=latest.customer_id,
        business_id=business_id,
    )


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
        lines.append(
            f"- {o.quantity}x {o.snapshot_product_name} — _{friendly_status(o.status.value)}_"
        )
    lines.append("\n_Reply with another order reference to check a different order._")
    return "\n".join(lines)


def _send_status_notification(order: Order, message: str) -> None:
    """Shared phone validation + send step for every order-status
    notification (paid, shipped, delivered, ...). Centralizing this means
    a phone-handling fix (like the to_e164 normalization) only has to
    happen in one place, not once per notify_* function."""
    phone = (
        to_e164(order.snapshot_customer_phone)
        if order.snapshot_customer_phone
        else None
    )
    if not phone:
        print(
            f"[order_notification] Skipped — invalid/missing phone for order {order.id}: {order.snapshot_customer_phone!r}"
        )
        return
    send_text_message(to_phone=phone, message=message)


def notify_shipping(order: Order, business: User, db: Session) -> None:
    location_line = (
        f"\nYou can collect it at: {business.delivery_location}"
        if business.delivery_location
        else ""
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
        if business.delivery_location
        else ""
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
        if was_paid
        else ""
    )
    message = (
        f"❌ Update: *{order.snapshot_product_name}* from your order "
        f"#{str(order.order_group_id or order.id)[:8]} with {business.business_name} "
        f"has been *cancelled*.{refund_line}\n\n"
        "_Reply 'status' anytime to see all your items, or 'menu' to shop again._"
    )
    _send_status_notification(order, message)


def load_session_product(session: MarketplaceSession, db: Session) -> Product | None:
    """Loads session.selected_product_id, scoped to session.selected_business_id.

    Replaces `db.query(Product).get(session.selected_product_id)`, which looked
    up a product by primary key with no tenant predicate at all. selected_
    product_id outlives a store switch, so an id belonging to store A could be
    loaded while the customer was in store B — and the awaiting_quantity branch
    would then hand it to add_item_to_cart against store B's cart, producing an
    Order row with store B's business_id and store A's product_id.

    is_available is included so an item pulled from sale mid-flow drops the
    customer back to the product list instead of being added to a cart.
    """
    if not session.selected_product_id or not session.selected_business_id:
        return None

    return (
        db.query(Product)
        .filter(
            Product.id == session.selected_product_id,
            Product.business_id == session.selected_business_id,
            Product.is_available,
        )
        .first()
    )


def handle_marketplace_step(
    session: MarketplaceSession, message: str, db: Session
) -> tuple[str, list[str] | None]:
    categories = get_all_categories(db)
    if not categories:
        return (
            "Sorry, no categories are available right now. Please try again later.",
            None,
        )

    # Secondary, pre-store-entry staleness check. The primary TTL now lives in
    # get_or_create_marketplace_session (MARKETPLACE_SESSION_TTL, 15 min) and
    # covers customers inside a store too, which this branch never could.
    if session.pending_action is not None and session.selected_business_id is None:
        is_stale = session.updated_at is not None and (
            datetime.now(timezone.utc) - session.updated_at
        ) > timedelta(hours=SESSION_TIMEOUT_HOURS)
        if is_stale:
            session.pending_action = None
            session.selected_business_type = None
            session.selected_category = None
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
            if is_business_question(message):
                return (
                    (
                        "That sounds like a question for a specific store — "
                        "pick a category below first, then the store, and "
                        "I'll help you get an answer."
                    ),
                    _menu_items_for_offset(titled_categories, _get_offset(session)),
                )
            return "Sorry, please reply with a number from the list above.", None

        matched_category = next((c for c in categories if c.title() == choice), None)
        if matched_category is None:
            # _resolve_choice returned an option that is no longer in the
            # category list (it was deactivated between the menu render and
            # the reply). Re-render rather than raising StopIteration, which is
            # what the bare next() here used to do.
            return (
                "That option isn't available anymore — please pick another.",
                _menu_items_for_offset(titled_categories, 0),
            )

        businesses = get_businesses_by_category(db, matched_category)

        if not businesses:
            return (
                "No stores found for that category right now. Please choose another.",
                None,
            )

        # The CATEGORY goes in selected_category. selected_business_type is
        # left for the business's own classification, set once a store is
        # actually chosen in the select_business branch below.
        session.selected_category = matched_category
        session.pending_action = "select_business"
        session.list_offset = 0
        db.commit()
        store_names = [b.business_name.strip() for b in businesses]
        return "Here are stores for you:", _menu_items_for_offset(store_names, 0)

    if session.pending_action == "select_business":
        businesses = get_businesses_by_category(db, session.selected_category)
        store_names = [b.business_name.strip() for b in businesses]
        choice, next_page = _resolve_paginated_choice(message, store_names, session, db)

        if next_page is not None:
            return "Here are stores for you:", next_page

        if choice is None:
            if is_business_question(message):
                return (
                    (
                        "That's worth asking — pick a store below and I can "
                        "help answer it, or connect you with them directly."
                    ),
                    _menu_items_for_offset(store_names, _get_offset(session)),
                )
            return "Sorry, please reply with a number from the list above.", None

        chosen = next(
            (b for b in businesses if b.business_name.strip() == choice), None
        )
        if chosen is None:
            # Store deactivated (or renamed) between rendering the list and the
            # customer's reply. Re-render instead of raising StopIteration.
            return (
                "That store isn't available anymore — please pick another.",
                _menu_items_for_offset(store_names, 0),
            )

        session.selected_business_id = chosen.id
        # Now that a real store is chosen, selected_business_type finally holds
        # what its name claims: the store's own classification. Nothing reads it
        # for filtering — it's for analytics and for the top-level routing this
        # column was always meant to describe.
        session.selected_business_type = (
            chosen.business_type.value
            if getattr(chosen, "business_type", None) is not None
            else None
        )
        session.pending_action = "awaiting_product_choice"
        session.list_offset = 0
        db.commit()
        cart = get_or_create_cart(session.phone_number, chosen.id, db)

        products = get_products_for_business_category(
            db, chosen.id, session.selected_category
        )

        if not products:
            welcome = (
                f"Welcome to {chosen.business_name}! "
                "We don't have items in that category right now — want to see "
                "something else? Reply 'menu' to browse other stores."
            )
        else:
            # The has_photos branch used to exist here, but both arms built an
            # identical message — the photos are sent separately by
            # message_processor._send_product_photos, not from this text.
            product_text = format_product_list_for_business(
                db, chosen.id, session.selected_category
            )
            heading = (
                f"Here's what we have in {session.selected_category}"
                if session.selected_category
                else "Here's what we have"
            )
            welcome = (
                f"Welcome to {chosen.business_name}! {heading}:\n\n"
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
            session.selected_business_id, session.selected_category, message, db
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
        product = load_session_product(session, db)
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

        product = load_session_product(session, db)
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
        session.last_product_at = datetime.now(timezone.utc)
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
            db, session.selected_business_id, session.selected_category
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
            contact = session.phone_number

        # Confirm the store still exists and is active before creating orders
        # against it. This used to be db.query(User).get(...) with no active
        # check and no None guard, so a deactivated store produced an
        # AttributeError deep inside create_orders_from_cart (on
        # business.business_name) after the cart had already been read.
        business = (
            db.query(User)
            .filter(User.id == session.selected_business_id, User.is_active)
            .first()
        )
        if business is None:
            reset_to_menu(session, db)
            return (
                (
                    "Sorry, that store is no longer available. Reply 'menu' to "
                    "browse other stores."
                ),
                None,
            )

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
    category_name: str | None,
) -> str:
    """Public wrapper so message_processor.py can resend the product list (e.g.
    after an 'Add More' tap) without duplicating _format_product_list's logic.

    Inherits get_products_for_business_category's full-catalog fallback, so a
    session with no category selected now lists the store's products instead of
    rendering the "nothing in that category" message at a customer who is
    standing in a stocked store.
    """
    products = get_products_for_business_category(db, business_id, category_name)
    return _format_product_list(products)


def _format_numbered_list(items: list[str]) -> str:
    lines = []
    for i, item in enumerate(items):
        emoji = NUMBERS[i] if i < len(NUMBERS) else f"{i + 1}."
        lines.append(f"{emoji} {item}")
    return "\n".join(lines)


def _resolve_choice(text: str, options: list[str]):
    """Maps a customer reply onto one of `options`, by 1-based index or by an
    exact case-insensitive name match.

    The digit-length cap matters: `str.isdigit()` is True for arbitrarily long
    runs, and Python ints are unbounded, so a 100k-digit payload would be
    converted in full before the range check rejected it. Bounding the length
    first keeps this O(1) on hostile input.
    """
    if not text or not options:
        return None

    text = text.strip().lower()
    if not text:
        return None

    if text.isdigit():
        if len(text) > MAX_MENU_SELECTION_DIGITS:
            return None
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return options[idx]
        return None

    for opt in options:
        if opt.lower() == text:
            return opt
    return None

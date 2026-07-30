import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

load_dotenv(find_dotenv())

from app.ai.cache import (  # noqa : E402
    already_sent_image,
    clear_active_business,
    get_active_business,
    mark_image_sent,
    set_active_business,
)
from app.ai.service import (  # noqa: E402
    classify_handover_urgency,
    detect_language,
    get_or_create_conversation_state,
    normalize_phone,
    notify_handover,
    process_customer_message,
    save_message,
)
from app.database import get_db  # noqa: E402
from app.flows.marketplace_flow import (  # noqa: E402
<<<<<<< HEAD
    add_item_to_cart,
    create_orders_from_cart,
    extract_order_ref,
    format_cart_summary,
    format_order_status,
    format_product_list_for_business,
    friendly_status,
    get_latest_orders_for_business,
    get_latest_orders_for_customer,
    get_or_create_cart,
    get_or_create_marketplace_session,
    get_orders_by_reference,
    get_products_for_business_category,
    handle_marketplace_step,
    is_checkout_command,
    is_human_handover_request,
    is_photo_request,
    is_status_command,
    is_switch_command,
    parse_name_and_contact,
    parse_quantity,
    reset_after_checkout,
    reset_to_menu,
    resolve_product_choice,
    resolve_size_choice,
=======
    add_item_to_cart,create_orders_from_cart,extract_order_ref,format_cart_summary,
    format_order_status,format_product_list_for_business,get_latest_orders_for_business,
    get_latest_orders_for_customer,get_or_create_cart,get_or_create_marketplace_session,
    get_orders_by_reference,get_products_for_business_category,handle_marketplace_step,is_checkout_command,
    is_photo_request,is_status_command,is_switch_command,is_business_question,parse_name_and_contact,parse_quantity,
    reset_after_checkout,reset_to_menu,resolve_product_choice,resolve_size_choice,friendly_status,
>>>>>>> 49b8aea80e0ae7325ce7d5d4455f993b8892ef5d
)
from app.models import Customer, HandoverStatus, Product, User  # noqa: E402
from app.webhook.client import (  # noqa: E402
    send_browse_more_prompt,
    send_list_picker,
    send_text_message,
)
from app.webhook.parser import extract_message_data  # noqa: E402

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

MAX_PRODUCT_IMAGES = 5

# How long a customer's last-added product stays eligible as the implicit
# target of a bare "can I see a photo?" with no product named. Matches
# marketplace_flow.SESSION_TIMEOUT_HOURS so "recently active" means the
# same thing everywhere in this project rather than introducing a second,
# unrelated expiry rule. Bumped 30min -> 24h: WhatsApp conversations
# routinely span hours (lunch-break add-to-cart, evening follow-up), and
# 30 minutes was going stale in exactly the case this feature is most
# useful for. Past this window we'd rather ask which product than guess
# against something the customer may have forgotten about.
STALE_PHOTO_WINDOW = timedelta(hours=24)

UNSUPPORTED_MESSAGE = (
    "Sorry, I can only read text messages right now. Please type your question.\n\n"
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. Tafadhali andika swali lako."
)

def _build_public_image_url(image_path: str, base_url: str) -> str:
    encoded_path = quote(image_path.strip(), safe="/:")
    if encoded_path.startswith(("http://", "https://")):
        return encoded_path
    return f"{base_url}/{encoded_path.lstrip('/')}"


def find_product_image(
    response_text: str, business_id: uuid.UUID, db: Session
) -> tuple[str | None, uuid.UUID | None]:
    if not response_text:
        return None, None

    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Webhook] BASE_URL is missing")
        return None, None

    # Fetch only products that have an image stored
    products_with_images = (
        db.query(Product)
        .filter(
            Product.business_id == business_id,
            Product.image_url.isnot(None),
            Product.is_available.is_(True),
        )
        .all()
    )

    response_lower = response_text.lower()

    for product in products_with_images:
        if product.name.lower() in response_lower:
            public_url = _build_public_image_url(product.image_url, base_url)

            print(
                f"[Webhook] Matched product '{product.name}' "
                f"(ID: {product.id})-> image: {public_url}"
            )

            return public_url, product.id

    return None, None


def get_active_business_id(
    customer_phone: str, marketplace_session, db: Session
) -> uuid.UUID | None:
    """
    Resolve which business a customer's free-text message belongs to.

    Primary source: marketplace_session.selected_business_id — set the
    moment a customer picks a store, but CLEARED by reset_to_menu() after
    checkout completes or on a 'menu'/switch command (see
    marketplace_flow.reset_to_menu). Confirmed: a customer messaging
    right after checkout will have this as None even though they're
    still "in" that store's context as far as the AI fallthrough is
    concerned.

    Fallback: the customer's most recently active Customer row. Customer
    rows are permanently scoped to one business each (uq_customer_per_business),
    so this survives marketplace_session being reset out from under us.
    """
    if marketplace_session.selected_business_id:
        return marketplace_session.selected_business_id

    phone = normalize_phone(customer_phone)
    last_customer = (
        db.query(Customer)
        .filter(Customer.phone_number == phone)
        .order_by(Customer.last_seen.desc())
        .first()
    )
    return last_customer.business_id if last_customer else None


def _get_or_create_customer_for_business(
    phone_number: str, business_id: uuid.UUID, db: Session, profile_name: str | None = None
) -> Customer:
    """Business-scoped customer lookup/create — mirrors the pattern
    marketplace_flow.py's checkout branch already uses. Needed because
    app.ai.service.get_or_create_customer no longer accepts business_id,
    but Customer.business_id is NOT NULL and customers are scoped per
    (phone_number, business_id) via uq_customer_per_business.

    last_seen is refreshed on every touch (not just name backfill) —
    get_active_business_id() depends on this staying current so its
    fallback query picks the customer's truly most-recent business,
    not whichever business happened to be touched last for unrelated
    reasons."""
    phone = normalize_phone(phone_number)
    customer = (
        db.query(Customer)
        .filter(Customer.phone_number == phone, Customer.business_id == business_id)
        .first()
    )
    if not customer:
        customer = Customer(phone_number=phone, business_id=business_id, name=profile_name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
    else:
        customer.last_seen = func.now()
        if profile_name and not customer.name:
            customer.name = profile_name
        db.commit()
    return customer


def _send_product_photos(customer_phone: str, business_id: uuid.UUID, category_name: str, db: Session) -> None:
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Webhook] BASE_URL is missing — skipping product photos")
        return

    products = get_products_for_business_category(db, business_id, category_name)
    products_with_images = [p for p in products if p.image_url][:MAX_PRODUCT_IMAGES]

    for p in products_with_images:
        if already_sent_image(customer_id=customer_phone, business_id=business_id, product_id=p.id):
            continue

        public_url = _build_public_image_url(p.image_url, base_url)
        caption = f"{p.name} — Ksh {p.price}"
        if p.unit:
            caption += f" / {p.unit}"
        if p.variant_label and p.variant_options:
            caption += f"\n{p.variant_label}: {p.variant_options}"

        mark_image_sent(customer_id=customer_phone, business_id=business_id, product_id=p.id)
        send_text_message(to_phone=customer_phone, message=caption, media_url=public_url)


def _send_product_prompt(
    customer_phone: str, marketplace_session, product: Product, db: Session, customer: Customer, language: str
) -> None:
    marketplace_session.selected_product_id = product.id
    if product.variant_label and product.variant_options:
        marketplace_session.pending_action = "awaiting_size"
        db.commit()
        reply_text = (
            f"Great choice! *{product.name}* — Ksh {product.price}\n"
            f"{product.variant_label}: {product.variant_options}\n\n"
            "Which one would you like?"
        )
    else:
        marketplace_session.pending_action = "awaiting_quantity"
        db.commit()
        reply_text = f"Great choice! *{product.name}* — Ksh {product.price}\nHow many would you like?"

    save_message(
        customer_id=customer.id, business_id=marketplace_session.selected_business_id,
        role="assistant", content=reply_text, language=language, db=db,
    )
    send_text_message(to_phone=customer_phone, message=reply_text)


def _send_marketplace_reply(customer_phone: str, reply_text: str, reply_items: list[str] | None) -> None:
    if reply_items:
        send_list_picker(to_phone=customer_phone, body_text=reply_text, items=reply_items)
    else:
        send_text_message(to_phone=customer_phone, message=reply_text)


def _resolve_photo_target(marketplace_session, business_id: uuid.UUID, message_text: str, db: Session) -> Product | None:
    """Resolves which product a bare/explicit photo request refers to.

    1. If the customer named a product in this message, that wins outright.
    2. Otherwise, fall back to the product they most recently added to
       cart (last_product_id) — but only if that add happened within
       STALE_PHOTO_WINDOW. Past that window we'd rather the customer name
       a product than get sent a photo of something they may not even
       remember choosing.
    """
    matched_product = resolve_product_choice(
        business_id=business_id,
        category_name=marketplace_session.selected_business_type,
        message=message_text,
        db=db,
    )
    if matched_product:
        return matched_product

    if not marketplace_session.last_product_id:
        return None

    is_fresh = (
        datetime.now(timezone.utc) - marketplace_session.updated_at
    ) < STALE_PHOTO_WINDOW
    if not is_fresh:
        return None

    return db.query(Product).filter(Product.id == marketplace_session.last_product_id).first()


def _send_product_photo(
    customer_phone: str, business: User, product: Product, db: Session, customer: Customer, language: str
) -> None:
    """Sends one specific product's photo with a caption naming it, and logs
    the exchange. Shared by both the immediate-match path and the
    awaiting_photo_choice follow-up, so the caption/logging behavior can't
    drift between the two call sites."""
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    public_url = _build_public_image_url(product.image_url, base_url)
    caption = (
        f"Here's {product.name} — Ksh {product.price}\n\n"
        "Want to see other products? Reply 'menu' to browse by category, "
        "then reply with a product name to see its photo."
    )
    send_text_message(to_phone=customer_phone, message=caption, media_url=public_url)
    # Explicit request bypasses already_sent_image entirely — that's the
    # whole point — but still marks it sent so a later automatic mention
    # doesn't immediately resend it a second time.
    mark_image_sent(customer_id=customer_phone, business_id=business.id, product_id=product.id)
    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                 content=caption, language=language, db=db)


def _send_fallback_reply(
    customer_phone: str, business_id: uuid.UUID, customer: Customer, language: str, reply_text: str, db: Session
) -> None:
    """Shared no-match/dead-state reply used by every awaiting_* branch
    below that previously had no explicit 'else' — those branches used to
    fall all the way through to process_customer_message() (the LLM) when
    nothing matched, which produces a plausible-sounding but state-blind
    reply (see the "one-stop shop" bug: a customer's stray message while
    mid-flow got answered by the AI instead of by the deterministic flow
    it was actually in). Every deterministic state now replies for itself
    instead of silently falling through."""
    save_message(customer_id=customer.id, business_id=business_id, role="assistant",
                 content=reply_text, language=language, db=db)
    send_text_message(to_phone=customer_phone, message=reply_text)


def _handle_deterministic_handover_request(
    customer_phone: str, business: User, customer: Customer, language: str, message_text: str, db: Session,
) -> None:
    """Single centralized bypass for every deterministic marketplace state
    below (awaiting_size, awaiting_quantity, awaiting_cart_action, etc.).
    Called once, right before that dispatch, so an explicit 'I need a
    human' can never be swallowed by a state-specific fallback reply like
    'Please reply with just a number, e.g. 2'. Reuses the exact same
    ConversationState + HandoverService pipeline app.ai.service.
    process_customer_message uses for LLM-triggered handovers, so both
    entry points produce one consistent HandoverEvent/notification
    behavior — including the same 'already escalated' dedup so repeated
    'I need a human' messages while waiting don't file duplicate events."""
    state = get_or_create_conversation_state(customer.id, business.id, db)

    if state.status in (HandoverStatus.HUMAN_ACTIVE, HandoverStatus.NEEDS_HUMAN):
        reply_text = "You're connected with our team — they'll be with you shortly!"
    else:
        state.status = HandoverStatus.NEEDS_HUMAN
        db.commit()
        urgency = classify_handover_urgency(message_text)
        notify_handover(
            customer.id, business.id, message_text, urgency, db,
            conversation_id=state.id, ai_summary=None,
        )
        reply_text = "Let me connect you with our team — they'll be with you shortly!"

    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                 content=reply_text, language=language, db=db)
    send_text_message(to_phone=customer_phone, message=reply_text)


@router.post("")
async def receive_message(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Twilio calls this every time a customer sends a WhatsApp message.

    Twilio sends form-encoded data (not JSON) so we read the raw form.
    We always return HTTP 200 — even on errors — to stop Twilio retrying
    the same message and sending duplicates to the customer.
    """
    try:
        t_start = time.time()
        # Read Twilio's form-encoded payload
        form = await request.form()
        form_data = dict(form)

        print(f"[Webhook] Incoming payload: {form_data}")

        # Parse into flat dict we can work with
        data = extract_message_data(form_data)

        if data is None:
            # Status callback or unrecognised event — ignore safely
            return Response(status_code=200)

        customer_phone = data["phone_number"]
        message_text = data["message_text"]
        message_type = data["message_type"]
        profile_name = data.get("customer_name")
        # Interactive taps carry a stable id here regardless of the
        # button's visible label — parser.py sets message_text to the
        # LABEL when present, so button_payload is what tap-matching
        # below should key off of, not message_text.
        button_payload = data.get("button_payload")

        # ── Unsupported type (image, voice note, sticker) ────────────
        if message_type not in ("text", "interactive") or not message_text:
            print(f"[Webhook] Unsupported type '{message_type}' from {customer_phone}")
            send_text_message(customer_phone, UNSUPPORTED_MESSAGE)
            return Response(status_code=200)

        print(f"[Webhook] Message from {customer_phone}: {message_text}")
        
        marketplace_session = get_or_create_marketplace_session(customer_phone, db)
        t_session = time.time()
        print(f"[TIMING] session lookup: {t_session - t_start:.2f}s")

        if is_switch_command(message_text):
            reset_to_menu(marketplace_session, db)
            clear_active_business(customer_phone)
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)
            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            return Response(status_code=200)

        # ── "Track order" quick-reply tap (from aisha_post_checkout_fridah) ──
        if button_payload == "track_order" or message_text.strip().lower() == "track_order" or is_status_command(message_text):
            order_ref = extract_order_ref(message_text)
            if order_ref:
                orders = get_orders_by_reference(order_ref, customer_phone, db)
            elif marketplace_session.selected_business_id:
                orders = get_latest_orders_for_business(
                    customer_phone, marketplace_session.selected_business_id, db
                )
                if not orders:
                    current_business = (
                        db.query(User).filter(User.id == marketplace_session.selected_business_id).first()
                    )
                    business_label = current_business.business_name if current_business else "this store"
                    reply_text = (
                        f"You don't have an order with {business_label} yet.\n\n"
                        "If you have an order reference from another store, reply "
                        "with it to check that order's status, or reply 'switch' "
                        "to browse other businesses."
                    )
                    send_text_message(to_phone=customer_phone, message=reply_text)
                    return Response(status_code=200)
            else:
                orders = get_latest_orders_for_customer(customer_phone, db)
            reply_text = format_order_status(orders)
            send_text_message(to_phone=customer_phone, message=reply_text)
            return Response(status_code=200)

        # ── "Browse more" quick-reply tap (from aisha_post_checkout_fridah) ──
        if button_payload == "browse_more":
            if marketplace_session.selected_business_id and marketplace_session.selected_business_type:
                marketplace_session.pending_action = "awaiting_product_choice"
                marketplace_session.list_offset = 0
                db.commit()
                product_text = format_product_list_for_business(
                    db, marketplace_session.selected_business_id, marketplace_session.selected_business_type
                )
                send_text_message(to_phone=customer_phone, message=product_text)
            else:
                reply_text, reply_items = handle_marketplace_step(marketplace_session, "menu", db)
                _send_marketplace_reply(customer_phone, reply_text, reply_items)
            return Response(status_code=200)

        # ── Reopen the last store instead of showing the top-level menu ──
        if marketplace_session.selected_business_id is None:
            cached_business_id = get_active_business(customer_phone)
            if cached_business_id:
                try:
                    reopened_business_id = uuid.UUID(cached_business_id)
                except (ValueError, AttributeError, TypeError):
                    reopened_business_id = None
                    print(f"[Webhook] Malformed active_biz cache value: {cached_business_id!r}")
 
                if reopened_business_id:
                    still_active = (
                        db.query(User)
                        .filter(User.id == reopened_business_id, User.is_active)
                        .first()
                    )
                    if still_active:
                        marketplace_session.selected_business_id = reopened_business_id
                        marketplace_session.selected_business_type = None
                        marketplace_session.pending_action = None
                        db.commit()
                    else:
                        clear_active_business(customer_phone)
        if marketplace_session.selected_business_id is None:
            if is_human_handover_request(message_text):
                # No store selected yet, so there's no business to file a
                # HandoverEvent against (business_id is NOT NULL). Ask which
                # store first instead of silently replying with the
                # 'please choose a number' category-list fallback.
                reply_text = (
                    "I'd love to connect you with a real person! Could you first "
                    "tell me which store you're shopping with (reply 'menu' to see "
                    "the list), so I can put you in touch with the right team?"
                )
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)

            just_entered_store = marketplace_session.selected_business_id is not None
            if just_entered_store:
                # Side effects (customer create/log, product photos) are
                # best-effort here — wrapped so a mid-request DB hiccup
                # (e.g. Neon dropping the connection) can't eat the actual
                # reply below. Previously these ran un-guarded ahead of
                # _send_marketplace_reply, so a crash here meant the store
                # selection got committed to the DB but the customer never
                # heard back — their next message then landed in a
                # pending_action state with no idea how it got there.
                try:
                    set_active_business(customer_phone, marketplace_session.selected_business_id)
                    customer = _get_or_create_customer_for_business(
                        customer_phone, marketplace_session.selected_business_id, db, profile_name=profile_name
                    )
                    language = detect_language(message_text)
                    save_message(customer_id=customer.id, business_id=marketplace_session.selected_business_id,
                                  role="user", content=message_text, language=language, db=db)
                    save_message(customer_id=customer.id, business_id=marketplace_session.selected_business_id,
                                  role="assistant", content=reply_text, language=language, db=db)
                    _send_product_photos(
                        customer_phone=customer_phone,
                        business_id=marketplace_session.selected_business_id,
                        category_name=marketplace_session.selected_business_type,
                        db=db,
                    )
                except Exception as side_effect_error:
                    print(f"[Webhook] Post-store-entry side effect failed: {side_effect_error}")

            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            return Response(status_code=200)

        # ── Multi-tenancy lookup ──────────────────────────────────────
        active_business_id = marketplace_session.selected_business_id
        if active_business_id is None:
            cached_business_id = get_active_business(customer_phone)
            if cached_business_id:
                try:
                    active_business_id = uuid.UUID(cached_business_id)
                except (ValueError, AttributeError, TypeError):
                    print(f"[Webhook] Malformed active_biz cache value: {cached_business_id!r}")
                    
        business = None
        if active_business_id:
            business = (
                db.query(User)
                .filter(User.id == active_business_id, User.is_active)
                .first()
            )

        if not business:
            marketplace_session.selected_business_id = None
            marketplace_session.pending_action = None
            db.commit()
            clear_active_business(customer_phone)
            send_text_message(to_phone=customer_phone, message="That store isn't available anymore. Let's find you another!")
            return Response(status_code=200)

        set_active_business(customer_phone, business.id)

        customer = _get_or_create_customer_for_business(customer_phone, business.id, db, profile_name=profile_name)
        language = detect_language(message_text)
        save_message(
            customer_id=customer.id,
            business_id=business.id,
            role="user",
            content=message_text,
            language=language,
            db=db,
        )

        # ── Human handover bypass ─────────────────────────────────────
        # Single centralized check, run before every deterministic
        # marketplace branch below (is_photo_request and the whole
        # awaiting_* dispatch), so none of them can swallow an explicit
        # request to speak with a human/agent/owner.
        if is_human_handover_request(message_text):
            _handle_deterministic_handover_request(customer_phone, business, customer, language, message_text, db)
            return Response(status_code=200)

        if is_photo_request(message_text):
            matched_product = _resolve_photo_target(marketplace_session, business.id, message_text, db)

            if matched_product and matched_product.image_url:
                _send_product_photo(customer_phone, business, matched_product, db, customer, language)
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                return Response(status_code=200)

            marketplace_session.pending_action = "awaiting_photo_choice"
            db.commit()
            reply_text = format_product_list_for_business(
                db, business.id, marketplace_session.selected_business_type
            )
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=reply_text, language=language, db=db)
            send_text_message(to_phone=customer_phone, message=reply_text)
            return Response(status_code=200)

        action = marketplace_session.pending_action

        if action == "awaiting_product_choice":
            matched_product = resolve_product_choice(
                business_id=business.id,
                category_name=marketplace_session.selected_business_type,
                message=message_text,
                db=db,
            )
            if matched_product:
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                return Response(status_code=200)

            # No match — previously fell through to the AI here with no
            # awareness the customer was mid product-selection.
            reply_text = (
                "Sorry, please reply with a product name from the list above, "
                "or 'menu' to start over."
            )
            _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
            return Response(status_code=200)

        elif action == "awaiting_photo_choice":
            # Follow-up to the "which product?" list sent above. Deterministic
            # match only — no LLM involved, same philosophy as every other
            # numbered/named selection in this file (category, store, size).
            matched_product = resolve_product_choice(
                business_id=business.id,
                category_name=marketplace_session.selected_business_type,
                message=message_text,
                db=db,
            )
            if matched_product and matched_product.image_url:
                # No explicit pending_action=None here — _send_product_prompt
                # below sets it to awaiting_size/awaiting_quantity itself,
                # same reasoning as the block above.
                _send_product_photo(customer_phone, business, matched_product, db, customer, language)
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                return Response(status_code=200)

            if matched_product and not matched_product.image_url:
                marketplace_session.pending_action = None
                db.commit()
                reply_text = f"Sorry, we don't have a photo for {matched_product.name} yet — happy to describe it though!"
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

            # No match — re-show the list rather than silently drop into
            # the AI (which would risk the same false "can't share photos"
            # reply this whole change exists to avoid).
            reply_text = "Sorry, please reply with a product name from the list above:\n\n" + format_product_list_for_business(
                db, business.id, marketplace_session.selected_business_type
            )
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=reply_text, language=language, db=db)
            send_text_message(to_phone=customer_phone, message=reply_text)
            return Response(status_code=200)

        elif action == "awaiting_size":
            product = db.query(Product).filter(Product.id == marketplace_session.selected_product_id).first()
            if not product:
                marketplace_session.pending_action = None
                marketplace_session.selected_product_id = None
                db.commit()
                # Previously fell through to the AI with no return here —
                # a deleted/deactivated product mid-flow used to silently
                # produce an LLM-generated reply instead of this.
                reply_text = "Sorry, that product is no longer available. Reply 'menu' to browse again."
                _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
                return Response(status_code=200)
            else:
                chosen_size = resolve_size_choice(message_text, product.variant_options)
                if not chosen_size:
                    reply_text = f"Please choose one of: {product.variant_options}"
                    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                                 content=reply_text, language=language, db=db)
                    send_text_message(to_phone=customer_phone, message=reply_text)
                    return Response(status_code=200)
                marketplace_session.selected_size = chosen_size
                marketplace_session.pending_action = "awaiting_quantity"
                db.commit()
                reply_text = "How many would you like?"
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

        elif action == "awaiting_quantity":
            product = db.query(Product).filter(Product.id == marketplace_session.selected_product_id).first()
            qty = parse_quantity(message_text)
            if not product:
                marketplace_session.pending_action = None
                marketplace_session.selected_product_id = None
                marketplace_session.selected_size = None
                db.commit()
                # Same fix as awaiting_size above — reply instead of
                # silently falling through to the AI.
                reply_text = "Sorry, that product is no longer available. Reply 'menu' to browse again."
                _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
                return Response(status_code=200)
            elif qty is None:
                reply_text = "Please reply with just a number, e.g. 2"
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)
            else:
                cart = get_or_create_cart(customer_phone, business.id, db)
                add_item_to_cart(cart, product, marketplace_session.selected_size, qty, db)
                marketplace_session.last_product_id = product.id
                marketplace_session.selected_product_id = None
                marketplace_session.selected_size = None
                marketplace_session.pending_action = "awaiting_cart_action"
                db.commit()
                line_total = qty * float(product.price)
                reply_text = (
                    f"Added: {qty}x {product.name} — Ksh {line_total:.2f}\n\n"
                    f"{format_cart_summary(cart)}\n\n"
                    "Reply 'checkout' to complete your order, or send another "
                    "product name/number to add more."
                )
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

        elif action == "awaiting_cart_action":
            if is_checkout_command(message_text):
                marketplace_session.pending_action = "awaiting_checkout_info"
                db.commit()
                reply_text = "Almost done! Please share your name and contact number."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

            matched_product = resolve_product_choice(
                business_id=business.id,
                category_name=marketplace_session.selected_business_type,
                message=message_text,
                db=db,
            )
            if matched_product:
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                return Response(status_code=200)
            
            # NEW: "do you have a purple one?" / "where is your store?" / "where
            # do you deliver?" — hand off to a human AND answer immediately via
            # AI, so the customer isn't left waiting on the owner to notice.
            # marketplace_session.pending_action is deliberately left untouched
            # here (still "awaiting_cart_action") — process_customer_message()
            # doesn't manage cart state, so 'checkout' or another product name
            # still works normally on the customer's next message.
            if is_business_question(message_text):
                result = process_customer_message(
                    phone_number=customer_phone, message_text=message_text,
                    business_id=business.id, db=db, profile_name=profile_name,
                )
                reply_text = result.get("response") or (
                    "Let me connect you with the team to check on that — they'll be with you shortly."
                )
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[Webhook] Handover flagged (business question) for customer {customer_phone}, business {business.id}: {message_text!r}")
                return Response(status_code=200)

            # Neither a checkout command nor a recognizable product —
            # previously fell through to the AI here.
            reply_text = (
                "Sorry, I didn't recognize that. Reply 'checkout' to complete "
                "your order, or send a product name to add more."
            )
            _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
            return Response(status_code=200)

        elif action == "awaiting_checkout_info":
            t_before_cart = time.time()
            cart = get_or_create_cart(customer_phone, business.id, db)
            t_after_cart = time.time()
            print(f"[TIMING] get_or_create_cart: {t_after_cart - t_before_cart:.2f}s")
            
            
            if not cart.items:
                marketplace_session.pending_action = None
                db.commit()
                reply_text = "Your cart is empty — let's find you something! Reply 'menu' to browse."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)
            
            #Customer
            if is_checkout_command(message_text):
                reply_text = "Please share your name and contact number to complete your order, e.g. 'John 0712345678'."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

            name, contact = parse_name_and_contact(message_text)
            if not contact:
                contact = customer_phone

            t_before_orders = time.time()
            orders = create_orders_from_cart(cart, business, customer, name, contact, db)
            t_after_orders = time.time()
            print(f"[TIMING] create_orders_from_cart: {t_after_orders - t_before_orders:.2f}s")

            order_ref = (
                str(orders[0].order_group_id)[:8]
                if orders and orders[0].order_group_id
                else "N/A"
            )
            item_lines = [
                f"- {o.quantity}x {o.snapshot_product_name} — Ksh {o.total_amount:.2f} — _{friendly_status(o.status.value)}_"
                for o in orders
            ]
            total = sum(o.total_amount for o in orders)

            confirmation_text = (
                f"Thank you, {name}! Your order has been placed ✅\n"
                f"Order reference: #{order_ref}\n\n"
                + "\n".join(item_lines)
                + f"\n\nTotal: Ksh {total:.2f}\n\n"
                f"We'll contact you at {contact} to confirm payment & delivery.\n\n"
                "_Each item is tracked separately, so status may update at different times._"
            )
            
            t_before_save= time.time()
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=confirmation_text, language=language, db=db)
            t_after_save = time.time()
            print(f"[TIMING] save_message (confirmation): {t_after_save - t_before_save:.2f}s")

            cart.items = []
            t_before_reset = time.time()
            reset_after_checkout(marketplace_session, db)
            t_after_reset = time.time()
            print(f"[TIMING] reset_after_checkout: {t_after_reset - t_before_reset:.2f}s")
            
            t_before_send = time.time()
            send_browse_more_prompt(to_phone=customer_phone, body_text=confirmation_text)
            t_after_send = time.time()
            print(f"[TIMING] twilio send (checkout): {t_after_send - t_before_send:.2f}s | total: {t_after_send - t_start:.2f}s")
            return Response(status_code=200)

        # ── Process through AISHA's AI engine (only reached on fall-through) ──
        t_before_ai = time.time()
        result = process_customer_message(
            phone_number=customer_phone, message_text=message_text,
            business_id=business.id, db=db, profile_name=profile_name,
        )
        t_after_ai = time.time()
        print(f"[TIMING] AI call: {t_after_ai - t_before_ai:.2f}s")

        if not result.get("response"):
            print("[Webhook] AISHA returned no response")
            return Response(status_code=200)

        media_url = None
        matched_image_url, product_id = find_product_image(result["response"], business.id, db)

        if matched_image_url and product_id:
            marketplace_session.last_product_id = product_id
            db.commit()

            customer_id = result["customer_id"]
            if already_sent_image(customer_id=customer_id, business_id=business.id, product_id=product_id):
                pass
            else:
                media_url = matched_image_url
                mark_image_sent(customer_id=customer_id, business_id=business.id, product_id=product_id)

        sent = send_text_message(to_phone=customer_phone, message=result["response"], media_url=media_url)
        t_after_send = time.time()
        print(f"[TIMING] twilio send: {t_after_send - t_after_ai:.2f}s | total: {t_after_send - t_start:.2f}s")
        
        
        if not sent:
            print(f"[Webhook] Failed to deliver reply to {customer_phone}")

        if result["needs_handover"]:
            print(f"[Webhook] Handover flagged for customer {customer_phone}")
        return Response(status_code=200)

    except Exception as e:
        print(f"[Webhook] Unhandled error: {e}")
        return Response(status_code=200)
    
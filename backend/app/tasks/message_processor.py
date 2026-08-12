import asyncio
import os
import time
import uuid
from datetime import timedelta, timezone, datetime
from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.cache import (
    acquire_customer_lock,
    already_sent_image,
    clear_active_business,
    get_active_business,
    mark_image_sent,
    release_customer_lock,
    set_active_business,
)
from app.ai.service import (
    detect_language,
    normalize_phone,
    process_customer_message,
    save_message,
)
from app.database import SessionLocal, async_session_factory
from app.models import ConversationState, Customer, HandoverStatus, Product, User
from app.webhook.client import send_browse_more_prompt, send_list_picker, send_text_message
from app.flows.marketplace_flow import (
    add_item_to_cart, create_orders_from_cart, extract_order_ref, format_cart_summary,
    format_order_status, format_product_list_for_business, get_latest_orders_for_business,
    get_category_id_for_business, get_latest_orders_for_customer, get_or_create_cart,
    get_or_create_marketplace_session, get_orders_by_reference, get_products_for_business_category,
    handle_marketplace_step, is_checkout_command, is_photo_request, is_status_command,
    is_switch_command, parse_name_and_contact, parse_quantity, reset_after_checkout,
    reset_to_menu, resolve_product_choice, resolve_size_choice, friendly_status,
    find_mentioned_alternate_variant, looks_like_question, _resolve_photo_target,
    _parse_sizes, _format_numbered_list,
)
from app.flows.reply_composer import compose

MAX_PRODUCT_IMAGES = 5
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


def find_product_image(response_text: str, business_id: uuid.UUID, db: Session) -> tuple[str | None, uuid.UUID | None]:
    if not response_text:
        return None, None
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Worker] BASE_URL is missing")
        return None, None
    products_with_images = (
        db.query(Product)
        .filter(Product.business_id == business_id, Product.image_url.isnot(None), Product.is_available.is_(True))
        .all()
    )
    response_lower = response_text.lower()
    for product in products_with_images:
        if product.name.lower() in response_lower:
            public_url = _build_public_image_url(product.image_url, base_url)
            print(f"[Worker] Matched product '{product.name}' (ID: {product.id})-> image: {public_url}")
            return public_url, product.id
    return None, None


def _get_or_create_customer_for_business(
    phone_number: str, business_id: uuid.UUID, db: Session, profile_name: str | None = None
) -> Customer:
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
        print("[Worker] BASE_URL is missing — skipping product photos")
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
        facts = f"*{product.name}* — Ksh {product.price}\n{product.variant_label}: {product.variant_options}"
        reply_text = compose(opener_key="product_pick", closer_key="ask_size", facts=facts)
    else:
        marketplace_session.pending_action = "awaiting_quantity"
        db.commit()
        facts = f"*{product.name}* — Ksh {product.price}"
        reply_text = compose(opener_key="product_pick", closer_key="ask_quantity", facts=facts)
    save_message(customer_id=customer.id, business_id=marketplace_session.selected_business_id,
                 role="assistant", content=reply_text, language=language, db=db)
    t0 = time.time()
    send_text_message(to_phone=customer_phone, message=reply_text)
    print(f"[TIMING] _send_product_prompt Twilio send: {time.time() - t0:.2f}s")


def _send_marketplace_reply(customer_phone: str, reply_text: str, reply_items: list[str] | None) -> None:
    t0 = time.time()
    if reply_items:
        send_list_picker(to_phone=customer_phone, body_text=reply_text, items=reply_items)
    else:
        send_text_message(to_phone=customer_phone, message=reply_text)
    print(f"[TIMING] _send_marketplace_reply Twilio send: {time.time() - t0:.2f}s")


def _send_product_photo(
    customer_phone: str, business: User, product: Product, db: Session, customer: Customer, language: str
) -> None:
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    public_url = _build_public_image_url(product.image_url, base_url)
    caption = (
        f"Here's {product.name} — Ksh {product.price}\n\n"
        "Want to see other products? Reply 'menu' to browse by category, "
        "then reply with a product name to see its photo."
    )
    t0 = time.time()
    send_text_message(to_phone=customer_phone, message=caption, media_url=public_url)
    print(f"[TIMING] _send_product_photo Twilio send: {time.time() - t0:.2f}s")
    mark_image_sent(customer_id=customer_phone, business_id=business.id, product_id=product.id)
    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                 content=caption, language=language, db=db)


def _send_fallback_reply(
    customer_phone: str, business_id: uuid.UUID, customer: Customer, language: str, reply_text: str, db: Session
) -> None:
    save_message(customer_id=customer.id, business_id=business_id, role="assistant",
                 content=reply_text, language=language, db=db)
    t0 = time.time()
    send_text_message(to_phone=customer_phone, message=reply_text)
    print(f"[TIMING] _send_fallback_reply Twilio send: {time.time() - t0:.2f}s")


def _is_negligible_input(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) <= 1:
        return True
    return not any(ch.isalnum() for ch in stripped)


def _looks_like_variant_attempt(text: str) -> bool:
    """A loose signal that the customer is trying to answer a size/variant
    prompt rather than saying something unrelated. See original docstring —
    unchanged from the RQ-migration session."""
    return any(ch.isdigit() for ch in text)


def _run_ai_call(
    customer_phone: str, business_id: uuid.UUID, message_text: str, db: Session, profile_name: str | None
) -> dict:
    """process_customer_message() is now `async def` — it needs an
    AsyncSession to build the prompt from the knowledge base
    (KnowledgeBaseManager / wiki_chunks). This worker job runs fully
    synchronously (RQ calls job functions with no event loop already
    running), so each AI call gets its own short-lived event loop and
    AsyncSession, opened and closed immediately around just that one
    call — not held for the life of the job. `db` (the sync Session)
    still gets passed through unchanged; only the knowledge-base lookup
    needs the async session."""
    async def _inner():
        async with async_session_factory() as async_db:
            return await process_customer_message(
                phone_number=customer_phone, message_text=message_text,
                business_id=business_id, db=db, async_db=async_db,
                profile_name=profile_name,
            )
    return asyncio.run(_inner())


def _ask_ai(
    customer_phone: str, business_id: uuid.UUID, message_text: str, db: Session, profile_name: str | None
) -> str | None:
    t0 = time.time()
    result = _run_ai_call(customer_phone, business_id, message_text, db, profile_name)
    print(f"[TIMING] _ask_ai (AI call): {time.time() - t0:.2f}s")
    if result.get("not_understood"):
        return None
    return result.get("response") or None


def _reanchor_after_ai_variant_answer(
    marketplace_session, product: Product, ai_answer: str | None, message_text: str, db: Session
) -> str:
    """Unchanged from the RQ-migration session — see original docstring."""
    if not ai_answer or not product.variant_options:
        return ai_answer or "Reply with a valid quantity number to choose how many you want."

    if looks_like_question(message_text) or not _looks_like_variant_attempt(message_text):
        return ai_answer

    sizes = _parse_sizes(product.variant_options)
    marketplace_session.selected_size = None
    marketplace_session.pending_action = "awaiting_size"
    db.commit()
    return ai_answer + "\n\n" + _format_numbered_list(sizes)


def process_customer_message_job(data: dict) -> None:
    """RQ job entrypoint. See original docstring for the lock/ordering
    rationale — unchanged.

    NEW in this version: after the customer is resolved for the active
    business, checks ConversationState.status. Only HUMAN_ACTIVE (the
    owner has explicitly clicked "take over" via
    PATCH /conversations/{id}/takeover) silences AISHA entirely — this
    is the "matching comment on the handover gate" that
    app/ai/service.py's process_customer_message() docstring refers to.
    NEEDS_HUMAN (AISHA flagged + notified, but no one has taken over
    yet) does NOT gate — AISHA keeps answering normally until an owner
    actually takes over, per service.py's own comment. Without this
    check here, nothing in the codebase ever stops the deterministic
    flow / AI fall-through from running after a human takes over, so
    the owner's manual replies (send_manual_reply in
    app/conversations/router.py) would get talked over by AISHA on the
    customer's very next message.
    """
    t_job_start = time.time()
    db = SessionLocal()
    t_db_opened = time.time()
    print(f"[TIMING] DB session open: {t_db_opened - t_job_start:.2f}s")

    customer_phone = data["phone_number"]
    message_text = data["message_text"]
    profile_name = data.get("customer_name")
    button_payload = data.get("button_payload")

    t_lock_start = time.time()
    lock_token = acquire_customer_lock(customer_phone, timeout_seconds=60)
    print(f"[TIMING] lock acquire: {time.time() - t_lock_start:.2f}s")

    if lock_token is None:
        print(f"[Worker] Lock timeout for {customer_phone} — investigate stuck lock, message not processed")
        db.close()
        return

    try:
        t0 = time.time()
        marketplace_session = get_or_create_marketplace_session(customer_phone, db)
        print(f"[TIMING] get_or_create_marketplace_session: {time.time() - t0:.2f}s")

        if is_switch_command(message_text):
            reset_to_menu(marketplace_session, db)
            clear_active_business(customer_phone)
            t0 = time.time()
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)
            print(f"[TIMING] handle_marketplace_step (switch): {time.time() - t0:.2f}s")
            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        if button_payload == "track_order" or message_text.strip().lower() == "track_order" or is_status_command(message_text):
            order_ref = extract_order_ref(message_text)
            if order_ref:
                orders = get_orders_by_reference(order_ref, customer_phone, db)
            elif marketplace_session.selected_business_id:
                orders = get_latest_orders_for_business(customer_phone, marketplace_session.selected_business_id, db)
                if not orders:
                    current_business = db.query(User).filter(User.id == marketplace_session.selected_business_id).first()
                    business_label = current_business.business_name if current_business else "this store"
                    reply_text = (
                        f"You don't have an order with {business_label} yet.\n\n"
                        "If you have an order reference from another store, reply "
                        "with it to check that order's status, or reply 'switch' "
                        "to browse other businesses."
                    )
                    send_text_message(to_phone=customer_phone, message=reply_text)
                    print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                    return
            else:
                orders = get_latest_orders_for_customer(customer_phone, db)
            reply_text = format_order_status(orders)
            send_text_message(to_phone=customer_phone, message=reply_text)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

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
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        if marketplace_session.selected_business_id is None:
            cached_business_id = get_active_business(customer_phone)
            if cached_business_id:
                try:
                    reopened_business_id = uuid.UUID(cached_business_id)
                except (ValueError, AttributeError, TypeError):
                    reopened_business_id = None
                    print(f"[Worker] Malformed active_biz cache value: {cached_business_id!r}")
                if reopened_business_id:
                    still_active = db.query(User).filter(User.id == reopened_business_id, User.is_active).first()
                    if still_active:
                        marketplace_session.selected_business_id = reopened_business_id
                        marketplace_session.selected_business_type = None
                        marketplace_session.pending_action = None
                        db.commit()
                    else:
                        clear_active_business(customer_phone)

        if marketplace_session.selected_business_id is None:
            t0 = time.time()
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)
            print(f"[TIMING] handle_marketplace_step: {time.time() - t0:.2f}s")

            just_entered_store = marketplace_session.selected_business_id is not None
            if just_entered_store:
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
                    t0 = time.time()
                    _send_product_photos(
                        customer_phone=customer_phone,
                        business_id=marketplace_session.selected_business_id,
                        category_name=marketplace_session.selected_business_type,
                        db=db,
                    )
                    print(f"[TIMING] _send_product_photos: {time.time() - t0:.2f}s")
                except Exception as side_effect_error:
                    print(f"[Worker] Post-store-entry side effect failed: {side_effect_error}")

            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        active_business_id = marketplace_session.selected_business_id
        if active_business_id is None:
            cached_business_id = get_active_business(customer_phone)
            if cached_business_id:
                try:
                    active_business_id = uuid.UUID(cached_business_id)
                except (ValueError, AttributeError, TypeError):
                    print(f"[Worker] Malformed active_biz cache value: {cached_business_id!r}")

        business = None
        if active_business_id:
            business = db.query(User).filter(User.id == active_business_id, User.is_active).first()

        if not business:
            marketplace_session.selected_business_id = None
            marketplace_session.pending_action = None
            db.commit()
            clear_active_business(customer_phone)
            reply_text = compose(opener_key="store_gone", closer_key="browse_menu")
            send_text_message(to_phone=customer_phone, message=reply_text)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        set_active_business(customer_phone, business.id)

        customer = _get_or_create_customer_for_business(customer_phone, business.id, db, profile_name=profile_name)
        language = detect_language(message_text)
        save_message(customer_id=customer.id, business_id=business.id, role="user",
                     content=message_text, language=language, db=db)

        # ── Human-handover gate ──────────────────────────────────────
        # Only HUMAN_ACTIVE silences AISHA — see function docstring.
        conv_state = (
            db.query(ConversationState)
            .filter_by(customer_id=customer.id, business_id=business.id)
            .first()
        )
        if conv_state and conv_state.status == HandoverStatus.HUMAN_ACTIVE:
            print(f"[Worker] Skipping automation — owner has taken over for {customer_phone}")
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        if is_photo_request(message_text):
            matched_product = _resolve_photo_target(marketplace_session, business.id, message_text, db)
            if matched_product and matched_product.image_url:
                _send_product_photo(customer_phone, business, matched_product, db, customer, language)
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return
            marketplace_session.pending_action = "awaiting_photo_choice"
            db.commit()
            reply_text = format_product_list_for_business(db, business.id, marketplace_session.selected_business_type)
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=reply_text, language=language, db=db)
            t0 = time.time()
            send_text_message(to_phone=customer_phone, message=reply_text)
            print(f"[TIMING] Twilio send: {time.time() - t0:.2f}s")
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        action = marketplace_session.pending_action

        if action == "awaiting_product_choice":
            matched_product = resolve_product_choice(
                business_id=business.id, category_name=marketplace_session.selected_business_type,
                message=message_text, db=db,
            )
            if matched_product:
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return
            if _is_negligible_input(message_text):
                reply_text = compose(opener_key=None, closer_key="no_match")
            else:
                ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
                reply_text = ai_answer or compose(opener_key=None, closer_key="no_match")
            _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        elif action == "awaiting_photo_choice":
            matched_product = resolve_product_choice(
                business_id=business.id, category_name=marketplace_session.selected_business_type,
                message=message_text, db=db,
            )
            if matched_product and matched_product.image_url:
                _send_product_photo(customer_phone, business, matched_product, db, customer, language)
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return
            if matched_product and not matched_product.image_url:
                marketplace_session.pending_action = None
                db.commit()
                facts = f"we don't have a photo for {matched_product.name} yet — happy to describe it though!"
                reply_text = compose(opener_key="no_photo", closer_key=None, facts=facts)
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return
            if _is_negligible_input(message_text):
                ai_answer = None
            else:
                ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
            if ai_answer:
                reply_text = ai_answer
            else:
                product_list = format_product_list_for_business(db, business.id, marketplace_session.selected_business_type)
                facts = f"please reply with a product name from the list above:\n\n{product_list}"
                reply_text = compose(opener_key=None, closer_key=None, facts=facts)
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=reply_text, language=language, db=db)
            send_text_message(to_phone=customer_phone, message=reply_text)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        elif action == "awaiting_size":
            product = db.query(Product).filter(Product.id == marketplace_session.selected_product_id).first()
            if not product:
                marketplace_session.pending_action = None
                marketplace_session.selected_product_id = None
                db.commit()
                reply_text = "Sorry, that product is no longer available. Reply 'menu' to browse again."
                _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            chosen_size = resolve_size_choice(message_text, product.variant_options)
            if chosen_size:
                marketplace_session.selected_size = chosen_size
                marketplace_session.pending_action = "awaiting_quantity"
                db.commit()
                reply_text = "Reply with a valid quantity number to choose how many you want."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            sizes = _parse_sizes(product.variant_options)
            unavailable_term = find_mentioned_alternate_variant(
                message_text, business.id, marketplace_session.selected_business_type,
                product.variant_options, db,
            )
            if unavailable_term:
                facts = f"we don't have {unavailable_term} {product.name} available right now.\nWe do have: {', '.join(sizes)}."
                reply_text = compose(opener_key="unavailable_variant", closer_key="explore_alternatives", facts=facts)
            elif not _is_negligible_input(message_text):
                ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
                reply_text = _reanchor_after_ai_variant_answer(
                    marketplace_session, product, ai_answer, message_text, db
                )
            else:
                reply_text = compose(opener_key="invalid_size", closer_key=None, facts=product.variant_options)

            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=reply_text, language=language, db=db)
            send_text_message(to_phone=customer_phone, message=reply_text)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        elif action == "awaiting_quantity":
            product = db.query(Product).filter(Product.id == marketplace_session.selected_product_id).first()
            qty = parse_quantity(message_text)
            if not product:
                marketplace_session.pending_action = None
                marketplace_session.selected_product_id = None
                marketplace_session.selected_size = None
                db.commit()
                reply_text = "Sorry, that product is no longer available. Reply 'menu' to browse again."
                _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            elif qty is None:
                unavailable_term = find_mentioned_alternate_variant(
                    message_text, business.id, marketplace_session.selected_business_type,
                    product.variant_options or "", db,
                )
                if unavailable_term:
                    facts = f"we don't have {unavailable_term} {product.name} available right now."
                    reply_text = compose(opener_key="unavailable_variant", closer_key="explore_alternatives", facts=facts)
                elif not _is_negligible_input(message_text):
                    ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
                    reply_text = _reanchor_after_ai_variant_answer(
                        marketplace_session, product, ai_answer, message_text, db
                    )
                else:
                    reply_text = "Reply with a valid quantity number to choose how many you want."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            else:
                cart = get_or_create_cart(customer_phone, business.id, db)
                add_item_to_cart(cart, product, marketplace_session.selected_size, qty, db)
                marketplace_session.last_product_id = product.id
                marketplace_session.selected_product_id = None
                marketplace_session.selected_size = None
                marketplace_session.pending_action = "awaiting_cart_action"
                db.commit()
                line_total = qty * float(product.price)
                facts = f"{qty}x {product.name} — Ksh {line_total:.2f}\n\n{format_cart_summary(cart)}"
                reply_text = compose(opener_key="confirm_add", closer_key="post_add", facts=facts)
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

        elif action == "awaiting_cart_action":
            if is_checkout_command(message_text):
                marketplace_session.pending_action = "awaiting_checkout_info"
                db.commit()
                reply_text = "Almost done! Please share your name and contact number."
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            matched_product = resolve_product_choice(
                business_id=business.id, category_name=marketplace_session.selected_business_type,
                message=message_text, db=db,
            )
            if matched_product:
                _send_product_prompt(customer_phone, marketplace_session, matched_product, db, customer, language)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            if not _is_negligible_input(message_text):
                ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
                if ai_answer:
                    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                                 content=ai_answer, language=language, db=db)
                    send_text_message(to_phone=customer_phone, message=ai_answer)
                    # needs_human handling (state, HandoverEvent, notifications
                    # across dashboard/WhatsApp/email) all happens inside
                    # process_customer_message() itself now — see
                    # app/ai/service.py's notify_handover(). Nothing to do here.
                    print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                    return

            reply_text = compose(opener_key=None, closer_key="cart_no_match")
            _send_fallback_reply(customer_phone, business.id, customer, language, reply_text, db)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        elif action == "awaiting_checkout_info":
            cart = get_or_create_cart(customer_phone, business.id, db)
            if not cart.items:
                marketplace_session.pending_action = None
                db.commit()
                reply_text = compose(opener_key="empty_cart", closer_key="browse_menu")
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            if is_checkout_command(message_text):
                facts = "Please share your name and contact number to complete your order, e.g. 'John 0712345678'."
                reply_text = compose(opener_key="ask_checkout_info", closer_key=None, facts=facts)
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                return

            if not _is_negligible_input(message_text):
                ai_answer = _ask_ai(customer_phone, business.id, message_text, db, profile_name)
                if ai_answer:
                    reply_text = ai_answer + "\n\nWhenever you're ready, share your name and contact number to complete your order."
                    save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                                 content=reply_text, language=language, db=db)
                    send_text_message(to_phone=customer_phone, message=reply_text)
                    print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
                    return

            name, contact = parse_name_and_contact(message_text)
            if not contact:
                contact = customer_phone

            orders = create_orders_from_cart(cart, business, customer, name, contact, db)
            order_ref = str(orders[0].order_group_id)[:8] if orders and orders[0].order_group_id else "N/A"
            item_lines = [
                f"- {o.quantity}x {o.snapshot_product_name} — Ksh {o.total_amount:.2f} — _{friendly_status(o.status.value)}_"
                for o in orders
            ]
            total = sum(o.total_amount for o in orders)
            facts = (
                f"Thank you, {name}!\nOrder reference: #{order_ref}\n\n"
                + "\n".join(item_lines)
                + f"\n\nTotal: Ksh {total:.2f}\n\n"
                f"We'll contact you at {contact} to confirm payment & delivery.\n\n"
                "_Each item is tracked separately, so status may update at different times._"
            )
            confirmation_text = compose(opener_key="order_confirmed", closer_key=None, facts=facts)
            save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                         content=confirmation_text, language=language, db=db)
            cart.items = []
            reset_after_checkout(marketplace_session, db)
            send_browse_more_prompt(to_phone=customer_phone, body_text=confirmation_text)
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        # ── Fall-through to AISHA's AI engine ──
        t0 = time.time()
        result = _run_ai_call(customer_phone, business.id, message_text, db, profile_name)
        print(f"[TIMING] AI call (fall-through): {time.time() - t0:.2f}s")

        if not result.get("response"):
            print("[Worker] AISHA returned no response")
            print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
            return

        media_url = None
        matched_image_url, product_id = find_product_image(result["response"], business.id, db)
        if matched_image_url and product_id:
            marketplace_session.last_product_id = product_id
            db.commit()
            customer_id = result["customer_id"]
            if not already_sent_image(customer_id=customer_id, business_id=business.id, product_id=product_id):
                media_url = matched_image_url
                mark_image_sent(customer_id=customer_id, business_id=business.id, product_id=product_id)

        t0 = time.time()
        sent = send_text_message(to_phone=customer_phone, message=result["response"], media_url=media_url)
        print(f"[TIMING] Twilio send: {time.time() - t0:.2f}s")
        if not sent:
            print(f"[Worker] Failed to deliver reply to {customer_phone}")
        if result["needs_handover"]:
            print(f"[Worker] Handover flagged for customer {customer_phone}")
        print(f"[TIMING] TOTAL job time: {time.time() - t_job_start:.2f}s")
        return

    except Exception as e:
        print(f"[Worker] Unhandled error processing {customer_phone}: {e}")
        raise  # re-raise so RQ's Retry policy (set at enqueue time) fires

    finally:
        release_customer_lock(customer_phone, lock_token)
        db.close()
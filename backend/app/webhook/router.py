import os
import time
import uuid
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
    detect_language,
    normalize_phone,
    process_customer_message,
    save_message,
)

from app.models import Customer, Product, User  # noqa: E402
from app.webhook.client import send_browse_more_prompt, send_list_picker, send_text_message # noqa: E402
from app.webhook.parser import extract_message_data  # noqa: E402
from app.database import get_db  # noqa: E402
from app.flows.marketplace_flow import (  # noqa: E402
    add_item_to_cart,create_orders_from_cart,extract_order_ref,format_cart_summary,
    format_order_status,get_latest_orders_for_customer,get_or_create_cart,get_or_create_marketplace_session,
    get_orders_by_reference,get_products_for_business_category,handle_marketplace_step,is_checkout_command,
    is_status_command,is_switch_command,parse_name_and_contact,parse_quantity,
    reset_to_menu,resolve_product_choice,resolve_size_choice,
)


router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

MAX_PRODUCT_IMAGES = 5

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
    This is NOT hypothetical — it's what should have fired for the
    "Cartier" message in the 12:18 PM session, immediately after the
    Prada Handbag checkout reset the session to None.
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
        # Checked before the selected_business_id gate below because this
        # button is sent right after checkout, once reset_to_menu() has
        # already cleared the session — so by the time this tap arrives,
        # selected_business_id is None and it would otherwise fall into
        # the marketplace-menu branch instead of showing order status.
        # Matches on the button's raw id ("track_order") OR any typed
        # status keyword (is_status_command), so this also covers a
        # customer just typing "status" free-text at any point.
        if message_text.strip().lower() == "track_order" or is_status_command(message_text):
            order_ref = extract_order_ref(message_text)
            orders = (
                get_orders_by_reference(order_ref, customer_phone, db)
                if order_ref
                else get_latest_orders_for_customer(customer_phone, db)
            )
            reply_text = format_order_status(orders)
            send_text_message(to_phone=customer_phone, message=reply_text)
            return Response(status_code=200)

        # ── Reopen the last store instead of showing the top-level menu ──
        # reset_to_menu() (called after checkout) clears selected_business_id
        # but deliberately does NOT clear the active_biz:{phone} Redis key —
        # only an explicit switch command does that (see clear_active_business
        # above). So if selected_business_id is None but the cache still
        # holds a value, this customer didn't say "menu"/"switch" — they just
        # finished checkout and are still talking about that store (e.g.
        # "Cartier" right after a Prada Handbag order). Route them back into
        # that business instead of resetting them to the category menu.
        #
        # pending_action is intentionally left untouched here (not reset to
        # None) — a customer might still be mid-flow (e.g. "awaiting_quantity")
        # when selected_business_id got cleared some other way; only the
        # business identity is being restored, not the conversational step.
        
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
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)

            just_entered_store = marketplace_session.selected_business_id is not None
            if just_entered_store:
                set_active_business(customer_phone, marketplace_session.selected_business_id)
                customer = _get_or_create_customer_for_business(
                    customer_phone, marketplace_session.selected_business_id, db, profile_name=profile_name
                )
                language = detect_language(message_text)
                save_message(customer_id=customer.id, business_id=marketplace_session.selected_business_id,
                              role="user", content=message_text, language=language, db=db)
                save_message(customer_id=customer.id, business_id=marketplace_session.selected_business_id,
                              role="assistant", content=reply_text, language=language, db=db)
                try:
                    _send_product_photos(
                        customer_phone=customer_phone,
                        business_id=marketplace_session.selected_business_id,
                        category_name=marketplace_session.selected_business_type,
                        db=db,
                    )
                except Exception as photo_error:
                    print(f"[Webhook] Product photo send failed: {photo_error}")

            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            return Response(status_code=200)

        # ── Multi-tenancy lookup ──────────────────────────────────────
        # selected_business_id is the source of truth (set either by the
        # normal store-picker flow, or by the reopen-last-store block
        # above). The Redis cache (active_biz:{phone}) is used ONLY as a
        # fallback when selected_business_id is somehow still None here
        # (e.g. the cache existed but the DB row for that business was
        # deleted outright) — it never overrides a value the session
        # already has, since the session is the authoritative, DB-backed
        # field and the cache is just a speed-up for the common case.
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

        # Keep Redis in sync with the session's source of truth (covers the
        # case where selected_business_id was set before this cache existed).
        set_active_business(customer_phone, business.id)

        # From here on the customer is inside a specific store, so every
        # exchange has a real business to attribute it to — get/create the
        # Customer row and log the incoming message once, up front, so
        # every branch below shares the same customer/language rather than
        # re-deriving them (and risking drift) at each return point.
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

        elif action == "awaiting_size":
            product = db.query(Product).filter(Product.id == marketplace_session.selected_product_id).first()
            if not product:
                marketplace_session.pending_action = None
                marketplace_session.selected_product_id = None
                db.commit()
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
            elif qty is None:
                reply_text = "Please reply with just a number, e.g. 2"
                save_message(customer_id=customer.id, business_id=business.id, role="assistant",
                             content=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)
            else:
                cart = get_or_create_cart(customer_phone, business.id, db)
                add_item_to_cart(cart, product, marketplace_session.selected_size, qty, db)
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

            # customer/profile_name already resolved above — reuse rather
            # than re-fetch, so this branch can't end up logging under a
            # different Customer row than the rest of the exchange.
            t_before_orders = time.time()
            orders = create_orders_from_cart(cart, business, customer, name, contact, db)
            t_after_orders = time.time()
            print(f"[TIMING] create_orders_from_cart: {t_after_orders - t_before_orders:.2f}s")

            # order_group_id ties every line item from this one checkout
            # together — see marketplace_flow.create_orders_from_cart.
            # Built here (not in marketplace_flow) because this is the
            # message actually sent to the customer.
            order_ref = (
                str(orders[0].order_group_id)[:8]
                if orders and orders[0].order_group_id
                else "N/A"
            )
            item_lines = [
                f"- {o.quantity}x {o.snapshot_product_name} — Ksh {o.total_amount:.2f} — _{o.status.value}_"
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
            # Full reset (not just clearing pending_action) — without
            # clearing selected_business_id, the customer's next message
            # (even days later) would silently stay scoped to this store's
            # AI instead of reopening the marketplace. NOTE: this is exactly
            # what clears selected_business_id to None — get_active_business_id()
            # exists specifically to recover from that via the Customer-row
            # fallback on the customer's *next* message.
            t_before_reset = time.time()
            reset_to_menu(marketplace_session, db)
            t_after_reset = time.time()
            print(f"[TIMING] reset_to_menu: {t_after_reset - t_before_reset:.2f}s")
            
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
    
from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
from urllib.parse import quote

load_dotenv(find_dotenv())

from app.database import get_db   # noqa: E402
from app.models import User, Product   # noqa: E402
from app.ai.service import (  # noqa: E402
    process_customer_message, get_or_create_customer, save_message, detect_language,
)
from app.webhook.client import send_text_message, send_list_picker, send_browse_more_prompt    # noqa: E402
from app.webhook.parser import extract_message_data    # noqa: E402
from app.ai.cache import already_sent_image, mark_image_sent # noqa : E402
from app.flows.marketplace_flow import ( # noqa: E402
    get_or_create_marketplace_session, handle_marketplace_step, is_switch_command,
    is_checkout_command, reset_to_menu, get_products_for_business_category,
    resolve_product_choice, get_or_create_cart, resolve_size_choice,
    parse_quantity, add_item_to_cart, format_cart_summary,
    parse_name_and_contact, create_orders_from_cart,
)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

UNSUPPORTED_MESSAGE = (
    "Sorry, I can only read text messages right now. Please type your question.\n\n"
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. Tafadhali andika swali lako."
)

MAX_PRODUCT_IMAGES = 5

def _build_public_image_url(image_path: str, base_url: str) -> str:
    """Shared URL-building logic -  encodes spaces/special chars safely for
    Twilio and handles both already-absolute URLs and relative storage paths."""
    encoded_path = quote(image_path.strip(), safe="/:")
    if encoded_path.startswith(("http://", "https://")):
        return encoded_path
    return f"{base_url}/{encoded_path.lstrip('/')}"

def find_product_image(response_text: str, user_id: int, db: Session) -> tuple[str | None, int | None]:
    if not response_text:
        return None, None

    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Webhook] BASE_URL is missing")
        return None, None

    products_with_images = (
        db.query(Product)
        .filter(
            Product.user_id == user_id,
            Product.image_url.isnot(None),
            Product.is_available.is_(True),
        )
        .all()
    )

    response_lower = response_text.lower()

    for product in products_with_images:
        if product.name.lower() in response_lower:
            image_path = product.image_url.strip()
            public_url = _build_public_image_url(image_path, base_url)

            print(
                f"[Webhook] Matched product '{product.name}' "
                f"(ID: {product.id})-> image: {public_url}"
            )

            return public_url, product.id

    return None, None

def _send_product_photos(customer_phone: str, business_id: int, category_name: str, db: Session) -> None:
    """Sends one Twilio message per product photo when a customer first
    enters a store — Twilio only allows one media attachment per message,
    so this is a loop of separate messages, not one combined message.
    Uses the same already_sent_image/mark_image_sent dedup mechanism as
    the AI-conversation image path, so a customer re-entering the same
    store/category (e.g. via 'menu' then picking it again) doesn't get
    the same product photos re-sent."""
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Webhook] BASE_URL is missing — skipping product photos")
        return

    products = get_products_for_business_category(db, business_id, category_name)
    products_with_images = [p for p in products if p.image_url][:MAX_PRODUCT_IMAGES]

    for p in products_with_images:
        if already_sent_image(customer_id=customer_phone, user_id=business_id, product_id=p.id):
            print(f"[Webhook] Image already sent for product {p.id} to {customer_phone}; skipping.")
            continue

        public_url = _build_public_image_url(p.image_url, base_url)
        caption = f"{p.name} — Ksh {p.price}"
        if p.unit:
            caption += f" / {p.unit}"
        if p.variant_label and p.variant_options:
            caption += f"\n{p.variant_label}: {p.variant_options}"

        mark_image_sent(customer_id=customer_phone, user_id=business_id, product_id=p.id)
        send_text_message(to_phone=customer_phone, message=caption, media_url=public_url)


def _send_product_prompt(
    customer_phone: str, marketplace_session, product: Product, db: Session, customer, language: str
) -> None:
    """Shared by both entry points into the size/quantity chain
    (awaiting_product_choice match, and awaiting_cart_action -> adding
    another item) so the two code paths can't drift out of sync.

    Also the single place that logs AISHA's reply for this step — fixing
    logging here fixes it for both call sites at once, same reasoning as
    the original shared-helper design."""
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
        customer_id=customer.id,
        user_id=marketplace_session.selected_business_id,
        sender="assistant",
        message_text=reply_text,
        language=language,
        db=db,
    )
    send_text_message(to_phone=customer_phone, message=reply_text)


def _send_marketplace_reply(customer_phone: str, reply_text: str, reply_items: list[str] | None) -> None:
    """Single place that decides List Picker vs plain text for a
    handle_marketplace_step() result — used by both the switch-command
    branch and the fresh-session branch so they can't drift out of sync.

    NOTE: this path runs before a business is selected (top-level
    category/store browsing), so it is intentionally NOT logged to
    Conversation — Conversation.user_id is NOT NULL and there is no
    business to attribute these messages to yet."""
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
        form = await request.form()
        form_data = dict(form)

        print(f"[Webhook] Incoming payload: {form_data}")

        data = extract_message_data(form_data)

        if data is None:
            return Response(status_code=200)

        customer_phone = data["phone_number"]
        message_text   = data["message_text"]
        message_type   = data["message_type"]
        profile_name   = data.get("customer_name")

        if message_type not in ("text", "interactive") or not message_text:
            print(f"[Webhook] Unsupported type '{message_type}' from {customer_phone}")
            send_text_message(customer_phone, UNSUPPORTED_MESSAGE)
            return Response(status_code=200)

        print(f"[Webhook] Message from {customer_phone}: {message_text}")

        marketplace_session = get_or_create_marketplace_session(customer_phone, db)

        if is_switch_command(message_text):
            reset_to_menu(marketplace_session, db)
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)
            _send_marketplace_reply(customer_phone, reply_text, reply_items)
            return Response(status_code=200)

        if marketplace_session.selected_business_id is None:
            reply_text, reply_items = handle_marketplace_step(marketplace_session, message_text, db)

            just_entered_store = marketplace_session.selected_business_id is not None
            if just_entered_store:
                customer = get_or_create_customer(customer_phone, marketplace_session.selected_business_id, db, profile_name=profile_name)
                language = detect_language(message_text)
                save_message(customer_id=customer.id, user_id=marketplace_session.selected_business_id,
                            sender="customer", message_text=message_text, language=language, db=db)
                save_message(customer_id=customer.id, user_id=marketplace_session.selected_business_id,
                            sender="assistant", message_text=reply_text, language=language, db=db)
        
        
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

        business = (
            db.query(User)
            .filter(User.id == marketplace_session.selected_business_id, User.is_active)
            .first()
        )

        if not business:
            marketplace_session.selected_business_id = None
            marketplace_session.pending_action = None
            db.commit()
            send_text_message(
                to_phone=customer_phone,
                message="That store isn't available anymore. Let's find you another!"
            )
            return Response(status_code=200)

        # From here on the customer is inside a specific store, so every
        # exchange has a real business to attribute it to — get/create the
        # Customer row and log the incoming message once, up front, so
        # every branch below shares the same customer/language rather than
        # re-deriving them (and risking drift) at each return point.
        customer = get_or_create_customer(customer_phone, business.id, db, profile_name=profile_name)
        language = detect_language(message_text)
        save_message(
            customer_id=customer.id,
            user_id=business.id,
            sender="customer",
            message_text=message_text,
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
                    save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                                 message_text=reply_text, language=language, db=db)
                    send_text_message(to_phone=customer_phone, message=reply_text)
                    return Response(status_code=200)
                marketplace_session.selected_size = chosen_size
                marketplace_session.pending_action = "awaiting_quantity"
                db.commit()
                reply_text = "How many would you like?"
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                             message_text=reply_text, language=language, db=db)
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
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                             message_text=reply_text, language=language, db=db)
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
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                             message_text=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

        elif action == "awaiting_cart_action":
            if is_checkout_command(message_text):
                marketplace_session.pending_action = "awaiting_checkout_info"
                db.commit()
                reply_text = "Almost done! Please share your name and contact number."
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                             message_text=reply_text, language=language, db=db)
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
            cart = get_or_create_cart(customer_phone, business.id, db)
            if not cart.items:
                marketplace_session.pending_action = None
                db.commit()
                reply_text = "Your cart is empty — let's find you something! Reply 'menu' to browse."
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                             message_text=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)
            
            #Customer
            if is_checkout_command(message_text):
                reply_text = "Please share your name and contact number to complete your order, e.g. 'John 0712345678'."
                save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                            message_text=reply_text, language=language, db=db)
                send_text_message(to_phone=customer_phone, message=reply_text)
                return Response(status_code=200)

            name, contact = parse_name_and_contact(message_text)
            if not contact:
                contact = customer_phone

            # customer/profile_name already resolved above — reuse rather
            # than re-fetch, so this branch can't end up logging under a
            # different Customer row than the rest of the exchange.
            orders = create_orders_from_cart(cart, business, customer, name, contact, db)

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

            save_message(customer_id=customer.id, user_id=business.id, sender="assistant",
                         message_text=confirmation_text, language=language, db=db)

            cart.items = []
            # Full reset (not just clearing pending_action) — without
            # clearing selected_business_id, the customer's next message
            # (even days later) would silently stay scoped to this store's
            # AI instead of reopening the marketplace.
            reset_to_menu(marketplace_session, db)

            send_browse_more_prompt(to_phone=customer_phone, body_text=confirmation_text)
            return Response(status_code=200)

        # ── Process through AISHA's AI engine (only reached on fall-through) ──
        effective_message = message_text

        result = process_customer_message(
            phone_number=customer_phone,
            message_text=effective_message,
            user_id=business.id,
            db=db,
            profile_name=profile_name,
        )

        if not result.get("response"):
            print("[Webhook] AISHA returned no response")
            print(f"[Webhook] Full result: {result}")
            return Response(status_code=200)

        media_url = None

        matched_image_url, product_id = find_product_image(
            response_text=result["response"],
            user_id=business.id,
            db=db,
        )

        if matched_image_url and product_id:
            customer_id = customer_phone

            if already_sent_image(
                customer_id=customer_id,
                user_id=business.id,
                product_id=product_id,
            ):
                print(
                    f"[Webhook] Image already sent for product {product_id} "
                    f"to {customer_phone}; skipping."
                )
            else:
                media_url = matched_image_url
                mark_image_sent(
                    customer_id=customer_id,
                    user_id=business.id,
                    product_id=product_id,
                )
                print(
                    f"[Webhook] First image for product {product_id} "
                    f"to {customer_phone}; attaching image."
                )

        sent = send_text_message(
            to_phone=customer_phone,
            message=result["response"],
            media_url=media_url,
        )

        if not sent:
            print(f"[Webhook] Failed to deliver reply to {customer_phone}")

        if result["needs_handover"]:
            print(f"[Webhook] Handover flagged for customer{customer_phone}")
        return Response(status_code=200)

    except Exception as e:
        print(f"[Webhook] Unhandled error: {e}")
        return Response(status_code=200)
    
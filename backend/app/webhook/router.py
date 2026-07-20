import os
import uuid
from urllib.parse import quote

from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

load_dotenv(find_dotenv())

from app.ai.cache import already_sent_image, mark_image_sent  # noqa : E402
from app.ai.service import process_customer_message  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models import Product, User  # noqa: E402
from app.webhook.client import send_text_message  # noqa: E402
from app.webhook.parser import extract_message_data  # noqa: E402

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

UNSUPPORTED_MESSAGE = (
    "Sorry, I can only read text messages right now. Please type your question.\n\n"
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. Tafadhali andika swali lako."
)


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
            image_path = product.image_url.strip()

            # Encode spaces and special characters safely for Twilio.
            encoded_path = quote(image_path, safe="/:")

            if encoded_path.startswith(("http://", "https://")):
                public_url = encoded_path
            else:
                public_url = f"{base_url}/{encoded_path.lstrip('/')}"

            print(
                f"[Webhook] Matched product '{product.name}' "
                f"(ID: {product.id})-> image: {public_url}"
            )

            return public_url, product.id

    return None, None


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
        if message_type != "text" or not message_text:
            print(f"[Webhook] Unsupported type '{message_type}' from {customer_phone}")
            send_text_message(customer_phone, UNSUPPORTED_MESSAGE)
            return Response(status_code=200)

        print(f"[Webhook] Message from {customer_phone}: {message_text}")

        # ── Multi-tenancy lookup ──────────────────────────────────────
        # Sandbox: one shared Twilio number, so we use the first active business.
        # Production: each business gets their own Twilio number.
        # When that happens, look up by data["twilio_number"] instead.
        business = db.query(User).filter(User.is_active).first()

        if not business:
            print("[Webhook] No active business found — cannot process message")
            return Response(status_code=200)

<<<<<<< HEAD
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

=======
        # ── Process through AISHA's AI engine ────────────────────────
>>>>>>> origin/dev
        result = process_customer_message(
            phone_number=customer_phone,
            message_text=message_text,
            business_id=business.id,
            db=db,
            profile_name=profile_name,
        )

        if not result.get("response"):
            print("[Webhook] AISHA returned no response")
            print(f"[Webhook] Full result: {result}")
            return Response(status_code=200)

        # find product image to attach
        media_url = None

        matched_image_url, product_id = find_product_image(
            response_text=result["response"],
            business_id=business.id,
            db=db,
        )

        if matched_image_url and product_id:
            # Use the real Customer UUID (already resolved/created inside
            # process_customer_message) as the cache key — not the raw phone
            # string — so image-sent tracking stays consistent with the DB.
            customer_id = result["customer_id"]

            if already_sent_image(
                customer_id=customer_id,
                business_id=business.id,
                product_id=product_id,
            ):
                print(
                    f"[Webhook] Image already sent for product {product_id} "
                    f"to {customer_phone}; skipping."
                )
            else:
                media_url = matched_image_url

                # Mark it BEFORE sending so duplicate webhook requests do not
                # send the same image again.
                mark_image_sent(
                    customer_id=customer_id,
                    business_id=business.id,
                    product_id=product_id,
                )

                print(
                    f"[Webhook] First image for product {product_id} "
                    f"to {customer_phone}; attaching image."
                )

        # ── Send AISHA's reply to the customer ────────────────────────
        sent = send_text_message(
            to_phone=customer_phone,
            message=result["response"],
            media_url=media_url,
        )

        if not sent:
            print(f"[Webhook] Failed to deliver reply to {customer_phone}")

        # ── Notify owner if handover triggered ───────────────────────
        if result["needs_handover"]:
            print(f"[Webhook] Handover flagged for customer{customer_phone}")
        return Response(status_code=200)

    except Exception as e:
        print(f"[Webhook] Unhandled error: {e}")
        # Return 200 even on crash — prevents Twilio duplicate retries
        return Response(status_code=200)

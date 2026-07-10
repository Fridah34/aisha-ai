from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
from urllib.parse import quote

load_dotenv(find_dotenv())

from app.database import get_db   # noqa: E402
from app.models import User , Product   # noqa: E402
from app.ai.service import process_customer_message    # noqa: E402
from app.webhook.client import send_text_message     # noqa: E402
from app.webhook.parser import extract_message_data    # noqa: E402
from app.ai.cache import already_sent_image, mark_image_sent # noqa : E402
from app.flows.marketplace_flow import ( # noqa: E402
    get_or_create_marketplace_session, handle_marketplace_step, is_switch_command, reset_to_menu, get_products_for_business_category,
    resolve_product_choice,) 

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

def find_product_image(response_text:str, user_id: int, db:Session) -> tuple[str | None, int | None]: 
    if not response_text:
        return None, None
    
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    if not base_url:
        print("[Webhook] BASE_URL is missing")
        return None, None
    
    #Fetch only products that have an image stored
    products_with_images= (
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

        # Mark BEFORE sending, same reasoning as the AI-path image send:
        # avoids duplicate sends if this webhook call gets retried.
        mark_image_sent(customer_id=customer_phone, user_id=business_id, product_id=p.id)
        send_text_message(to_phone=customer_phone, message=caption, media_url=public_url)



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
        message_text   = data["message_text"]
        message_type   = data["message_type"]
        profile_name   = data.get("customer_name")

        # ── Unsupported type (image, voice note, sticker) ────────────
        if message_type != "text" or not message_text:
            print(f"[Webhook] Unsupported type '{message_type}' from {customer_phone}")
            send_text_message(customer_phone, UNSUPPORTED_MESSAGE)
            return Response(status_code=200)

        print(f"[Webhook] Message from {customer_phone}: {message_text}")
        
        # Marketplace lookup
        marketplace_session = get_or_create_marketplace_session(customer_phone, db)
        
        # --Switch-store command(works even mid-conversation in a store)
        if is_switch_command(message_text):
            reset_to_menu(marketplace_session, db)
            reply = handle_marketplace_step(marketplace_session, message_text, db)
            if reply:
                send_text_message(to_phone=customer_phone, message=reply)
            return Response(status_code=200)
        
        
        if marketplace_session.selected_business_id is None:
            reply = handle_marketplace_step(marketplace_session, message_text, db)
            if reply:
                 # If this reply just landed them inside a store (selected_business_id
                # got set this turn), send each product's photo as its own message
                # first, then the text summary last.
                just_entered_store = marketplace_session.selected_business_id is not None
                if just_entered_store:
                    try:
                        _send_product_photos(
                            customer_phone=customer_phone,
                            business_id=marketplace_session.selected_business_id,
                            category_name=marketplace_session.selected_business_type,
                            db=db,
                        )
                    except Exception as photo_error:
                        print(f"[Webhook] Product photo send failed: { photo_error}")
                send_text_message(to_phone=customer_phone, message=reply)
            return Response(status_code=200)
          
        # ── Multi-tenancy lookup ──────────────────────────────────────
        # Sandbox: one shared Twilio number, so we use the first active business.
        # Production: each business gets their own Twilio number.
        # When that happens, look up by data["twilio_number"] instead.
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
                message = "That store isn't available anymore. Let's find you another!"
            )
            return Response(status_code=200)
        
        # ── Resolve a pending product-list reply, if one is expected ──
        # Only clear pending_action on a SUCCESSFUL match. A failed match
        # (typo, near-miss, or a genuinely unrelated question) leaves the
        # flag in place so the customer isn't locked out of trying again —
        # their message still flows through to the AI unchanged either way.
        effective_message = message_text
        if marketplace_session.pending_action == "awaiting_product_choice":
            matched_product = resolve_product_choice(
                business_id=business.id,
                category_name=marketplace_session.selected_business_type,
                message=message_text,
                db=db,
            )
            if matched_product:
                marketplace_session.pending_action = None
                db.commit()
                effective_message = f"I'm interested in the {matched_product.name}"
        
        # ── Process through AISHA's AI engine ────────────────────────
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
        
        # find product image to attach
        media_url = None

        matched_image_url, product_id = find_product_image(
        response_text=result["response"],
        user_id=business.id,
        db=db,
        )

        if matched_image_url and product_id:
        # customer_phone is stable and unique for the WhatsApp customer.
        # Redis keys can safely use strings, so we use it as customer_id.
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

            # Mark it BEFORE sending so duplicate webhook requests do not
            # send the same image again.
                mark_image_sent(
                    customer_id=customer_id,
                    user_id=business.id,
                    product_id=product_id,
                )

                print(
                    f"[Webhook] First image for product {product_id} "
                    f"to {customer_phone}; attaching image."
                )

        # ── Send AISHA's reply to the customer ────────────────────────
        sent = send_text_message(
            to_phone=customer_phone, 
            message= result["response"],
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
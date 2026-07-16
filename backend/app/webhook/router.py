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

def find_product_image(response_text: str, business_id: uuid.UUID, db: Session) -> tuple[str | None, uuid.UUID | None]:
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
        message_text   = data["message_text"]
        message_type   = data["message_type"]
        profile_name   = data.get("customer_name")

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

        # ── Process through AISHA's AI engine ────────────────────────
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
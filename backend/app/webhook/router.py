import os
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from app.database import get_db
from app.models import User
from app.ai.service import process_customer_message
from app.webhook.client import send_text_message, send_owner_alert
from app.webhook.parser import extract_message_data

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

UNSUPPORTED_MESSAGE = (
    "Sorry, I can only read text messages right now. Please type your question.\n\n"
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. Tafadhali andika swali lako."
)


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
        business = db.query(User).filter(User.is_active == True).first()

        if not business:
            print(f"[Webhook] No active business found — cannot process message")
            return Response(status_code=200)

        # ── Process through AISHA's AI engine ────────────────────────
        result = process_customer_message(
            phone_number=customer_phone,
            message_text=message_text,
            user_id=business.id,
            db=db,
        )

        # ── Send AISHA's reply to the customer ────────────────────────
        sent = send_text_message(customer_phone, result["response"])

        if not sent:
            print(f"[Webhook] Failed to deliver reply to {customer_phone}")

        # ── Notify owner if handover triggered ───────────────────────
        if result["needs_handover"]:
            owner_phone = getattr(business, "whatsapp_phone_number", None)

            if owner_phone:
                send_owner_alert(
                    owner_phone=owner_phone,
                    customer_phone=customer_phone,
                    customer_message=message_text,
                    urgency=result.get("handover_urgency", "normal"),
                )
            else:
                print(
                    f"[Webhook] Handover triggered but owner has no "
                    f"whatsapp_phone_number set — cannot notify"
                )

        return Response(status_code=200)

    except Exception as e:
        print(f"[Webhook] Unhandled error: {e}")
        # Return 200 even on crash — prevents Twilio duplicate retries
        return Response(status_code=200)
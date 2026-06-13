# app/whatsapp/router.py

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from app.database import get_db  # noqa: E402
from app.models import User  # noqa: E402
from app.ai.service import process_customer_message   # noqa: E402
from app.whatsapp.client import send_text_message, send_owner_alert  # noqa: E402
from app.whatsapp.parser import extract_message_data  # noqa: E402

router = APIRouter(prefix="/webhook", tags=["webhook"])

UNSUPPORTED_MESSAGE_EN = (
    "Sorry, I can only read text messages right now. "
    "Could you please type your question?"
)
UNSUPPORTED_MESSAGE_SW = (
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. "
    "Tafadhali andika swali lako."
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_business_by_phone_number_id(
    phone_number_id: str,
    db: Session
) -> User | None:
    """
    Looks up which business registered this WhatsApp number.
    """
    return (
        db.query(User)
        .filter(User.whatsapp_phone_number_id == phone_number_id)
        .first()
    )


def update_customer_name(
    customer_id: int,
    name: str | None,
    db: Session
) -> None:
    """
    Saves the customer's WhatsApp display name if we don't have it yet.
    Meta includes the name in the first message payload.
    We only update if name is not already set — don't overwrite a
    name AISHA collected mid-conversation with a display name.
    """
    if not name:
        return

    from app.models import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer and not customer.name:
        customer.name = name
        db.commit()


# ── GET /webhook — Meta verification ─────────────────────────────────────────

@router.get("", response_class=PlainTextResponse)
@router.get("/", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """
    Meta calls this once when you register your webhook URL.
    They send a challenge string — you echo it back to prove
    you control the server. Without this, Meta rejects your webhook.

    Meta sends three query params:
      hub.mode           = "subscribe"
      hub.verify_token   = whatever you set in Meta dashboard
      hub.challenge      = a random string Meta wants echoed back
    """
    params = request.query_params

    mode    = params.get("hub.mode")
    token   = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and token == verify_token:
        print("[Webhook] Meta verification successful")
        return PlainTextResponse(content=challenge, status_code=200)

    print("[Webhook] Verification failed — token mismatch")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


# ── POST /webhook — incoming messages ────────────────────────────────────────

@router.post("")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    """
    Every WhatsApp message sent to any registered business hits this endpoint.
    Meta expects a 200 response within 15 seconds or it will retry delivery.

    We always return 200 immediately — even if processing fails —
    to prevent Meta from hammering the endpoint with retries.
    Errors are logged but never surfaced to Meta.
    """
    try:
        body = await request.json()
    except Exception:
        # Malformed JSON — return 200 anyway so Meta doesn't retry
        return {"status": "ignored"}

    # ── Parse the payload ─────────────────────────────────────────────────
    data = extract_message_data(body)

    if data is None:
        # Status update, read receipt, or unrecognised event — ignore
        return {"status": "ignored"}

    phone_number    = data["phone_number"]
    phone_number_id = data["phone_number_id"]
    message_text    = data["message_text"]
    customer_name   = data["customer_name"]
    message_type    = data["message_type"]

    # ── Find the business ─────────────────────────────────────────────────
    business = get_business_by_phone_number_id(phone_number_id, db)

    if not business:
        # No business registered for this WhatsApp number
        # Happens during testing with unregistered numbers — log and skip
        print(f"[Webhook] No business found for phone_number_id: {phone_number_id}")
        return {"status": "ignored"}

    # ── Handle unsupported message types ──────────────────────────────────
    # Voice notes, images, stickers — AISHA can't process these yet
    if message_type != "text":
        print(f"[Webhook] Unsupported type '{message_type}' from {phone_number}")
        # Send a polite reply asking them to type instead
        # Use English as default — we have no language signal yet
        send_text_message(
            to_phone=phone_number,
            message=UNSUPPORTED_MESSAGE_EN,
            phone_number_id=phone_number_id,
        )
        return {"status": "ok"}

    # ── Process the message through AISHA's engine ────────────────────────
    print(
        f"[Webhook] Message from {phone_number} "
        f"→ business '{business.business_name}'"
    )

    try:
        result = process_customer_message(
            phone_number=phone_number,
            message_text=message_text,
            user_id=business.id,
            db=db,
        )
    except Exception as e:
        print(f"[Webhook] Engine error for {phone_number}: {e}")
        # Send a graceful error message to the customer
        send_text_message(
            to_phone=phone_number,
            message=(
                "Samahani, kuna tatizo kidogo. Tafadhali jaribu tena.\n"
                "Sorry, something went wrong. Please try again."
            ),
            phone_number_id=phone_number_id,
        )
        return {"status": "ok"}

    # ── Send AISHA's response to the customer ─────────────────────────────
    sent = send_text_message(
        to_phone=phone_number,
        message=result["response"],
        phone_number_id=phone_number_id,
    )

    if not sent:
        print(f"[Webhook] Failed to send response to {phone_number}")

    # ── Save customer display name if we got it ───────────────────────────
    update_customer_name(result["customer_id"], customer_name, db)

    # ── Notify business owner if handover triggered ───────────────────────
    if result["needs_handover"]:
        owner_phone = getattr(business, "whatsapp_phone_number", None)

        if owner_phone:
            send_owner_alert(
                owner_phone=owner_phone,
                customer_phone=phone_number,
                customer_message=message_text,
                urgency=result.get("handover_urgency", "normal"),
                phone_number_id=phone_number_id,
            )
        else:
            print(
                "[Webhook] Handover triggered but owner has no "
                "whatsapp_phone_number set — cannot notify"
            )

    return {"status": "ok"}
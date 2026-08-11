from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import Response
from rq import Retry

load_dotenv(find_dotenv())

from app.ai.cache import is_duplicate_message  # noqa: E402
from app.queue import message_queue  # noqa: E402
from app.webhook.client import send_text_message  # noqa: E402
from app.webhook.parser import extract_message_data  # noqa: E402

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

UNSUPPORTED_MESSAGE = (
    "Sorry, I can only read text messages right now. Please type your question.\n\n"
    "Samahani, ninaweza kusoma maandishi tu kwa sasa. Tafadhali andika swali lako."
)


@router.post("")
async def receive_message(request: Request):
    """Twilio calls this on every incoming WhatsApp message. Does the
    minimum needed to ack fast: parse the payload, dedup the
    MessageSid, and enqueue the real work onto RQ. Always returns 200 —
    even for a message that fails downstream in the worker — so Twilio
    never retries a delivery we've already accepted responsibility for.
    """
    form = await request.form()
    form_data = dict(form)
    print(f"[Webhook] Incoming payload: {form_data}")

    data = extract_message_data(form_data)
    if data is None:
        # Status callback or unrecognised event — ignore safely
        return Response(status_code=200)

    message_sid = form_data.get("MessageSid") or form_data.get("SmsMessageSid")

    # Claimed synchronously, here — not inside the job. Two
    # near-simultaneous retries of the same Twilio delivery must not
    # both pass this check and both get enqueued.
    if is_duplicate_message(message_sid):
        print(f"[Webhook] Duplicate delivery ignored: {message_sid}")
        return Response(status_code=200)

    if data["message_type"] not in ("text", "interactive") or not data.get("message_text"):
        print(f"[Webhook] Unsupported type '{data['message_type']}' from {data['phone_number']}")
        send_text_message(data["phone_number"], UNSUPPORTED_MESSAGE)
        return Response(status_code=200)

    print(f"[Webhook] Message from {data['phone_number']}: {data['message_text']}")

    message_queue.enqueue(
        "app.tasks.message_processor.process_customer_message_job",
        data,
        retry=Retry(max=3, interval=[5, 30, 120]),
        job_timeout=120,
    )
    return Response(status_code=200)


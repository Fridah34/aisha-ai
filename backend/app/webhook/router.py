from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import Response
from rq import Retry

load_dotenv(find_dotenv())

from app.ai.cache import is_duplicate_message
from app.queue import message_queue
from app.timing import Stopwatch
from app.webhook.parser import extract_message_data

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])


@router.post("")
async def receive_message(request: Request):
    """
    Twilio calls this every time a customer sends a WhatsApp message.

    Thin dispatcher only — no DB/session work happens here. Parses the
    payload, dedups on Twilio's MessageSid, enqueues the real work to
    app.tasks.message_processor.process_customer_message_job, and always
    returns 200 immediately so Twilio doesn't retry-deliver the same
    message while a job is still running.
    """
    try:
        form = await request.form()
        form_data = dict(form)
        print(f"[Webhook] Incoming payload: {form_data}")

        sw = Stopwatch()

        data = extract_message_data(form_data)
        if data is None:
            return Response(status_code=200)

        message_sid = form_data.get("MessageSid") or form_data.get("SmsMessageSid")
        if message_sid and is_duplicate_message(message_sid):
            print(f"[Webhook] Duplicate MessageSid {message_sid} — skipping enqueue")
            return Response(status_code=200)

        sw.split("webhook_received")

        print(
            f"[Webhook] Message from {data['phone_number']}: {data.get('message_text')}"
        )

        # Carried into the worker process so it can report queue wait against
        # the same trace_id — the two halves run in different containers.
        data["trace_id"] = sw.trace_id

        message_queue.enqueue(
            "app.tasks.message_processor.process_customer_message_job",
            data,
            retry=Retry(max=3, interval=[5, 30, 120]),
            job_timeout=120,
        )
        sw.split("queue_enqueue")
        sw.total("webhook_TOTAL")
        return Response(status_code=200)

    except Exception as e:  # noqa: BLE001 — webhook must always ack 200 to Twilio, whatever the failure mode
        print(f"[Webhook] Unhandled error: {e}")
        return Response(status_code=200)

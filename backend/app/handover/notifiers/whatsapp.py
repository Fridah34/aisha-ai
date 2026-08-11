"""WhatsApp channel — reuses the existing Twilio send function
(app/webhook/client.py) that already sends outbound WhatsApp messages for
this project. `send_text_message` is sync/blocking, so it's dispatched via
`asyncio.to_thread` to stay non-blocking on the event loop."""

from __future__ import annotations

import asyncio
import logging

from app.handover.notifiers.base import Notifier
from app.handover.schemas import NotificationPayload
from app.webhook.client import send_text_message

logger = logging.getLogger(__name__)


class WhatsAppNotifier(Notifier):
    channel_key = "whatsapp"

    async def send(self, payload: NotificationPayload) -> bool:
        recipient = payload.business_notification_phone
        if not recipient:
            logger.warning(
                "[WhatsAppNotifier] Business %s has no whatsapp_phone_number configured; "
                "skipping handover notification.",
                payload.business_id,
            )
            return False

        message = (
            f"\U0001F514 Handover needed ({payload.reason_label})\n"
            f"Customer: {payload.customer_name or payload.customer_phone}\n"
            f"Waiting: {payload.waiting_time_label}\n"
            f"Message: \"{payload.customer_last_message}\""
        )

        try:
            return await asyncio.to_thread(send_text_message, recipient, message)
        except Exception:
            logger.exception(
                "[WhatsAppNotifier] Failed to send handover notification for business %s",
                payload.business_id,
            )
            return False

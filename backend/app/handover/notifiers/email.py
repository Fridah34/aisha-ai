"""Email channel — clean, connectable interface. See
`app/handover/notifiers/email_client.py` for why this is a stub: no email
provider exists in this project yet. The `Notifier` contract (send() ->
bool) is fully honored so this channel can go live by implementing
`email_client.send_email` without touching the notification engine."""

from __future__ import annotations

import logging

from app.handover.notifiers.base import Notifier
from app.handover.notifiers.email_client import is_configured, send_email
from app.handover.schemas import NotificationPayload

logger = logging.getLogger(__name__)


class EmailNotifier(Notifier):
    channel_key = "email"

    async def send(self, payload: NotificationPayload) -> bool:
        recipient = payload.business_notification_email
        if not recipient:
            logger.warning(
                "[EmailNotifier] Business %s has no notification email configured; "
                "skipping handover notification.",
                payload.business_id,
            )
            return False

        if not is_configured():
            logger.info(
                "[EmailNotifier] Email delivery is not configured; handover notification for "
                "business %s was not sent. reason=%s waiting=%s",
                payload.business_id,
                payload.reason_label,
                payload.waiting_time_label,
            )
            return False

        subject = f"Handover needed: {payload.reason_label}"
        body = (
            f"Customer: {payload.customer_name or payload.customer_phone}\n"
            f"Waiting: {payload.waiting_time_label}\n"
            f"Message: {payload.customer_last_message}\n"
        )
        try:
            return send_email(to_address=recipient, subject=subject, body=body)
        except Exception:
            logger.exception(
                "[EmailNotifier] Failed to send handover notification for business %s",
                payload.business_id,
            )
            return False

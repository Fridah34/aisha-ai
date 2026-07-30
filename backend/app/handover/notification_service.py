"""Configuration-driven notification dispatch.

`NotificationService` contains zero business logic about *when* a handover
should happen or *what* the reason is — that's decided upstream (AI service /
HandoverService). Given an already-created `HandoverEvent` and the owning
`User`, it only reads `User.handover_notifications` and, for each channel
that is enabled, asks the `NotificationScheduler` to deliver the shared
`NotificationPayload` after that channel's configured delay.
"""

from __future__ import annotations

from app.handover.notifiers import NOTIFIERS
from app.handover.reason_codes import reason_label
from app.handover.scheduler import NotificationScheduler
from app.handover.schemas import HandoverNotificationSettings, NotificationPayload
from app.handover.utils import format_waiting_duration
from app.models import HandoverEvent, User

_scheduler = NotificationScheduler()


def _build_payload(event: HandoverEvent, business: User) -> NotificationPayload:
    return NotificationPayload(
        business_id=event.business_id,
        conversation_id=event.conversation_id,
        customer_id=event.customer_id,
        customer_name=event.customer_name,
        customer_phone=event.customer_phone,
        reason_code=event.reason_code,
        reason=event.reason,
        reason_label=reason_label(event.reason_code),
        ai_summary=event.ai_summary,
        customer_last_message=event.customer_last_message,
        waiting_start_time=event.waiting_start_time,
        waiting_time_label=format_waiting_duration(event.waiting_start_time),
        status=event.status,
        business_notification_email=business.email,
        business_notification_phone=business.whatsapp_phone_number,
    )


class NotificationService:
    """Dispatches a `HandoverEvent` to every enabled channel, purely by
    reading the business's `handover_notifications` settings."""

    def notify(self, event: HandoverEvent, business: User) -> None:
        settings = HandoverNotificationSettings.model_validate(
            business.handover_notifications or {}
        )
        payload = _build_payload(event, business)

        for channel_key, channel_settings in settings.model_dump().items():
            if not channel_settings.get("enabled"):
                continue

            notifier = NOTIFIERS.get(channel_key)
            if notifier is None:
                continue

            _scheduler.schedule(
                notifier,
                payload,
                delay_minutes=channel_settings.get("delay_minutes", 0),
                event_id=event.id,
            )

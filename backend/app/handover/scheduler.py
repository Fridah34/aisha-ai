"""Delay-respecting, non-blocking notification scheduling.

No task queue (Celery/APScheduler/RQ) exists in this project. The webhook
handler that triggers a handover already runs on FastAPI's live event loop
(it's an `async def` route), so plain `asyncio.create_task` + `asyncio.sleep`
is sufficient here and requires zero new dependencies.

Each scheduled send opens its own DB session via `SessionLocal` at fire-time
(never reuses the original request-scoped session, which will already be
closed by the time a multi-minute delay elapses) and re-checks the event's
status — if the handover was already accepted/resolved/closed while a
delayed notification was pending, the send is skipped rather than
uselessly alerting the owner about something already handled.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.database import SessionLocal
from app.handover import crud
from app.handover.notifiers.base import Notifier
from app.handover.schemas import NotificationPayload
from app.models import HandoverEventStatus

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Schedules a single notifier's `send()` call, immediately or after a
    configured delay, without blocking the caller."""

    def schedule(
        self,
        notifier: Notifier,
        payload: NotificationPayload,
        *,
        delay_minutes: int,
        event_id: uuid.UUID,
    ) -> None:
        if delay_minutes <= 0:
            asyncio.create_task(self._fire(notifier, payload, event_id, check_status=False))
            return

        asyncio.create_task(
            self._fire_after_delay(notifier, payload, event_id, delay_minutes)
        )

    async def _fire_after_delay(
        self,
        notifier: Notifier,
        payload: NotificationPayload,
        event_id: uuid.UUID,
        delay_minutes: int,
    ) -> None:
        await asyncio.sleep(delay_minutes * 60)
        await self._fire(notifier, payload, event_id, check_status=True)

    async def _fire(
        self,
        notifier: Notifier,
        payload: NotificationPayload,
        event_id: uuid.UUID,
        *,
        check_status: bool,
    ) -> None:
        if check_status and not self._still_waiting(event_id):
            logger.info(
                "[NotificationScheduler] Skipping %s notification for event %s — "
                "no longer WAITING.",
                notifier.channel_key,
                event_id,
            )
            return

        try:
            sent = await notifier.send(payload)
            if not sent:
                logger.warning(
                    "[NotificationScheduler] %s notification for event %s reported failure.",
                    notifier.channel_key,
                    event_id,
                )
        except Exception:
            logger.exception(
                "[NotificationScheduler] Unhandled error sending %s notification for event %s",
                notifier.channel_key,
                event_id,
            )

    def _still_waiting(self, event_id: uuid.UUID) -> bool:
        """Opens a fresh session — the request that scheduled this send is
        long finished by the time a delayed notification fires."""
        db = SessionLocal()
        try:
            event = crud.get_event(db, event_id)
            return event is not None and event.status == HandoverEventStatus.WAITING
        finally:
            db.close()

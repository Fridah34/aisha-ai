"""Dashboard channel — the one channel this feature implements end-to-end.
Reuses the existing websocket `ConnectionManager` (app/websocket/router.py)
that already pushes real-time updates to a business's connected dashboard
clients; a handover notification is just one more message `type` on the
same socket."""

from __future__ import annotations

import logging

from app.handover.notifiers.base import Notifier
from app.handover.schemas import NotificationPayload
from app.websocket.router import manager

logger = logging.getLogger(__name__)


class DashboardNotifier(Notifier):
    channel_key = "dashboard"

    async def send(self, payload: NotificationPayload) -> bool:
        try:
            await manager.broadcast_to_business(
                payload.business_id,
                {
                    "type": "handover_notification",
                    "conversation_id": str(payload.conversation_id),
                    "customer_id": str(payload.customer_id),
                    "customer_name": payload.customer_name,
                    "customer_phone": payload.customer_phone,
                    "reason_code": payload.reason_code.value,
                    "reason_label": payload.reason_label,
                    "waiting_time_label": payload.waiting_time_label,
                    "customer_last_message": payload.customer_last_message,
                    "ai_summary": payload.ai_summary,
                    "status": payload.status.value,
                },
            )
            return True
        except Exception:
            logger.exception(
                "[DashboardNotifier] Failed to broadcast handover notification for business %s",
                payload.business_id,
            )
            return False

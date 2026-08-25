"""Orchestrates the Human Handover Notification system end-to-end:
creates the `HandoverEvent` audit row for a `[HANDOVER_REQUIRED]` trigger and
hands it to `NotificationService`; keeps the event's status in sync with the
conversation lifecycle (owner takeover / resolve actions).

This is the only module `app/ai/service.py` and
`app/conversations/router.py` need to import from `app.handover`.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.handover import crud
from app.handover.notification_service import NotificationService
from app.handover.reason_codes import classify_handover_reason
from app.models import HandoverEvent, HandoverEventStatus, User

_notification_service = NotificationService()


class HandoverService:
    @staticmethod
    def create_event_and_notify(
        db: Session,
        *,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        customer_id: uuid.UUID,
        customer_name: str | None,
        customer_phone: str,
        customer_last_message: str,
        ai_summary: str | None = None,
        reason: str | None = None,
    ) -> HandoverEvent:
        """Creates the `HandoverEvent` row and schedules notifications across
        every enabled channel. Called from `app.ai.service.notify_handover`
        whenever AISHA emits `[HANDOVER_REQUIRED]`."""
        reason_code = classify_handover_reason(customer_last_message)

        event = crud.create_event(
            db,
            business_id=business_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            reason_code=reason_code,
            reason=reason or customer_last_message,
            ai_summary=ai_summary,
            customer_last_message=customer_last_message,
        )

        business = db.query(User).filter(User.id == business_id).first()
        if business is not None:
            _notification_service.notify(event, business)

        return event

    @staticmethod
    def mark_accepted(
        db: Session, *, customer_id: uuid.UUID, business_id: uuid.UUID
    ) -> HandoverEvent | None:
        """Called when the owner takes over a conversation
        (PATCH /conversations/{customer_id}/takeover)."""
        event = crud.get_latest_open_event(
            db, customer_id=customer_id, business_id=business_id
        )
        if event is None:
            return None
        return crud.set_status(db, event, HandoverEventStatus.ACCEPTED)

    @staticmethod
    def mark_resolved(
        db: Session, *, customer_id: uuid.UUID, business_id: uuid.UUID
    ) -> HandoverEvent | None:
        """Called when the owner resolves a conversation
        (PATCH /conversations/{customer_id}/resolve)."""
        event = (
            db.query(HandoverEvent)
            .filter(
                HandoverEvent.customer_id == customer_id,
                HandoverEvent.business_id == business_id,
                HandoverEvent.status.in_(
                    [HandoverEventStatus.WAITING, HandoverEventStatus.ACCEPTED]
                ),
            )
            .order_by(HandoverEvent.created_at.desc())
            .first()
        )
        if event is None:
            return None
        return crud.set_status(db, event, HandoverEventStatus.RESOLVED)

"""
Pure SQLAlchemy reads/writes for `HandoverEvent`. Mirrors the style of
app/conversations/crud.py — plain functions, no ORM logic leaking into
the notification engine or the router layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import HandoverEvent, HandoverEventStatus, HandoverReasonCode


def create_event(
    db: Session,
    *,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_name: str | None,
    customer_phone: str,
    reason_code: HandoverReasonCode,
    reason: str,
    ai_summary: str | None,
    customer_last_message: str,
) -> HandoverEvent:
    """Creates the audit-trail row for a single [HANDOVER_REQUIRED] trigger."""
    event = HandoverEvent(
        business_id=business_id,
        conversation_id=conversation_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        reason_code=reason_code,
        reason=reason,
        ai_summary=ai_summary,
        customer_last_message=customer_last_message,
        waiting_start_time=datetime.now(timezone.utc),
        status=HandoverEventStatus.WAITING,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_event(db: Session, event_id: uuid.UUID) -> HandoverEvent | None:
    return db.query(HandoverEvent).filter(HandoverEvent.id == event_id).first()


def get_latest_open_event(
    db: Session, *, customer_id: uuid.UUID, business_id: uuid.UUID
) -> HandoverEvent | None:
    """Most recent event still awaiting a human (WAITING) for this customer —
    used to move an event to ACCEPTED/RESOLVED when the owner acts on the
    conversation, and by the scheduler to skip stale delayed notifications."""
    return (
        db.query(HandoverEvent)
        .filter(
            HandoverEvent.customer_id == customer_id,
            HandoverEvent.business_id == business_id,
            HandoverEvent.status == HandoverEventStatus.WAITING,
        )
        .order_by(HandoverEvent.created_at.desc())
        .first()
    )


def set_status(db: Session, event: HandoverEvent, status: HandoverEventStatus) -> HandoverEvent:
    event.status = status
    db.commit()
    db.refresh(event)
    return event

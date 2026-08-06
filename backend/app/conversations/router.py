"""
Conversations API — dashboard endpoints for the business owner.

AUTH: business_id comes from the authenticated session (get_current_user), never from the client.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.service import save_message
from app.auth.dependencies import get_current_user
from app.conversations import crud
from app.conversations.schemas import ConversationSummary, ConversationThread
from app.database import get_db
from app.handover import HandoverService
from app.models import ConversationState, Customer, HandoverStatus, User
from app.webhook.client import send_text_message

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationSummary])
def get_inbox(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_inbox(db, current_user.id)


@router.get("/{customer_id}", response_model=ConversationThread)
def get_thread(
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = crud.get_thread(db, customer_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


@router.patch("/{customer_id}/takeover")
def takeover_conversation(
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner takes over — AISHA stops auto-replying."""
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, business_id=current_user.id)
        .first()
    )
    if not state:
        # Auto-create state row for conversations that predate state tracking
        state = ConversationState(
            customer_id=customer_id,
            business_id=current_user.id,
            status=HandoverStatus.HUMAN_ACTIVE,
            taken_over_at=datetime.now(timezone.utc),
        )
        db.add(state)
    else:
        state.status = HandoverStatus.HUMAN_ACTIVE
        state.taken_over_at = datetime.now(timezone.utc)
    db.commit()
    HandoverService.mark_accepted(db, customer_id=customer_id, business_id=current_user.id)
    return {"status": state.status.value}


@router.patch("/{customer_id}/resolve")
def resolve_conversation(
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner marks done — AISHA resumes on next customer message."""
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, business_id=current_user.id)
        .first()
    )
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    state.status = HandoverStatus.RESOLVED
    state.resolved_at = datetime.now(timezone.utc)
    db.commit()
    HandoverService.mark_resolved(db, customer_id=customer_id, business_id=current_user.id)
    return {"status": state.status.value}


@router.post("/{customer_id}/reply")
def send_manual_reply(
    customer_id: uuid.UUID,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner sends a message directly to customer via Twilio, bypassing AISHA."""
    text = (payload.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Try Twilio — log failure but never crash
    # Will fail if ngrok is down or Twilio sandbox is inactive
    twilio_sent = send_text_message(customer.phone_number, text)
    if not twilio_sent:
        print(f"[Reply] Twilio failed for {customer.phone_number} — saving to DB only")

    # Always save to DB so the thread stays accurate
    save_message(
        customer_id=customer_id,
        business_id=current_user.id,
        role="human",
        content=text,
        language="en",
        db=db,
        delivery_status="delivered" if twilio_sent else "failed",
    )

    return {"sent": True, "twilio_delivered": twilio_sent}

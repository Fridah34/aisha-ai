"""
Conversations API — dashboard endpoints for the business owner.

AUTH: user_id now comes from the authenticated session (get_current_user), never from the client.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio

from app.models import ConversationState, HandoverStatus, User, Customer
from app.auth.dependencies import get_current_user
from app.ai.service import save_message
from app.webhook.client import send_text_message
from app.database import get_db
from app.conversations import crud
from app.conversations.schemas import ConversationSummary, ConversationThread
from app.websocket.router import manager

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# helper function to broadcast status changes
async def broadcast_status_change(user_id: int, customer_id: int, new_status: str):
    """Broadcast a status change to all websocket connections of a user"""
    message = {
        "type": "status_change",
        "customer_id": customer_id,
        "new_status": new_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast_to_user(user_id, message)


@router.get("", response_model=list[ConversationSummary])
def get_inbox(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_inbox(db, current_user.id)


@router.get("/{customer_id}", response_model=ConversationThread)
def get_thread(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = crud.get_thread(db, customer_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


@router.patch("/{customer_id}/takeover")
async def takeover_conversation(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner takes over — AISHA stops auto-replying."""
    user_id = current_user.id
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, user_id=user_id)
        .first()
    )
    if not state:
        # Auto-create state row for conversations that predate state tracking
        state = ConversationState(
            customer_id=customer_id,
            user_id=user_id,
            status=HandoverStatus.human_active,
            taken_over_at=datetime.now(timezone.utc),
        )
        db.add(state)
    else:
        state.status = HandoverStatus.human_active
        state.taken_over_at = datetime.now(timezone.utc)
    db.commit()

    await broadcast_status_change(user_id, customer_id, HandoverStatus.human_active.value)

    return {"status": state.status.value}


@router.patch("/{customer_id}/resolve")
async def resolve_conversation(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner marks done — AISHA resumes on next customer message."""
    user_id = current_user.id
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, user_id=user_id)
        .first()
    )
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    state.status = HandoverStatus.resolved
    state.resolved_at = datetime.now(timezone.utc)
    db.commit()

    await broadcast_status_change(user_id, customer_id, HandoverStatus.resolved.value)

    return {"status": state.status.value}


@router.post("/{customer_id}/reply")
def send_manual_reply(
    customer_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner sends a message directly to customer via Twilio, bypassing AISHA."""
    text = (payload.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.user_id == current_user.id)
        .first()
    )
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
        user_id=current_user.id,
        sender="human",
        message_text=text,
        language="en",
        db=db,
        delivery_status="delivered" if twilio_sent else "failed",
    )

    return {"sent": True, "twilio_delivered": twilio_sent}
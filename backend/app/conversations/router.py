"""
Conversations API — dashboard endpoints for the business owner.

AUTH NOTE: user_id is passed explicitly for now.
Replace with Depends(get_current_user) when Eve's JWT auth is ready.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio

from app.models import ConversationState, HandoverStatus, Customer
from app.ai.service import save_message
from app.webhook.client import send_text_message
from app.database import get_db
from app.conversations import crud
from app.conversations.schemas import ConversationSummary, ConversationThread
from app.websocket.router import manager

router = APIRouter(prefix="/conversations", tags=["Conversations"])

#helper fucntion to broadcast status changes
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
def get_inbox(user_id: int, db: Session = Depends(get_db)):
    result = crud.get_inbox(db, user_id)
    return result


@router.get("/{customer_id}", response_model=ConversationThread)
def get_thread(customer_id: int, user_id: int, db: Session = Depends(get_db)):
    thread = crud.get_thread(db, customer_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


@router.patch("/{customer_id}/takeover")
async def takeover_conversation(customer_id: int, user_id: int, db: Session = Depends(get_db)):
    """Owner takes over — AISHA stops auto-replying."""
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

    #Broadcast the status change
    await broadcast_status_change(user_id, customer_id, HandoverStatus.human_active.value)

    return {"status": state.status.value}


@router.patch("/{customer_id}/resolve")
async def resolve_conversation(customer_id: int, user_id: int, db: Session = Depends(get_db)):
    """Owner marks done — AISHA resumes on next customer message."""
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

    # Broadcast the status change
    await broadcast_status_change(user_id, customer_id, HandoverStatus.resolved.value)

    return {"status": state.status.value}


@router.post("/{customer_id}/reply")
def send_manual_reply(
    customer_id: int,
    user_id: int,
    payload: dict,
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
        user_id=user_id,
        sender="human",
        message_text=text,
        language="en",
        db=db,
        delivery_status="delivered" if twilio_sent else "failed",
    )

    return {"sent": True, "twilio_delivered": twilio_sent}
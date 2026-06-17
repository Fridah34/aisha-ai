"""
Conversations API — read-only endpoints for the dashboard.
Business owners can view their inbox and full chat threads.

AUTH NOTE: user_id is passed explicitly for now.
Replace with Depends(get_current_user) when Eve's JWT auth is ready.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.conversations import crud
from app.conversations.schemas import ConversationSummary, ConversationThread

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationSummary])
def get_inbox(user_id: int, db: Session = Depends(get_db)):
    """
    Returns the inbox — one row per customer showing their
    last message. Sorted newest first.
    Dashboard uses this to render the conversation list.
    """
    return crud.get_inbox(db, user_id)


@router.get("/{customer_id}", response_model=ConversationThread)
def get_thread(
    customer_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the full message thread for one customer.
    Scoped to the requesting business — cross-business isolation enforced.
    """
    thread = crud.get_thread(db, customer_id, user_id)
    if not thread:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )
    return thread
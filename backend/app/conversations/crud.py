"""
pure SQLAlchemy
"""
import uuid

from app.models import Conversation, ConversationState, Customer, HandoverStatus
from sqlalchemy import func
from sqlalchemy.orm import Session


def get_inbox(db: Session, business_id: uuid.UUID) -> list[dict]:
    """
    Returns one row per customer - their latest message and metadata.
    Used to render the inbox list on the dashboard.
    """
    latest = (
        db.query(
            Conversation.customer_id,
            func.max(Conversation.created_at).label("last_time"),
            func.count(Conversation.id).label("total")
        )
        .filter(Conversation.business_id == business_id)
        .group_by(Conversation.customer_id)
        .subquery()
    )
    
    #join back to get the actual message content at that created_at
    rows = (
        db.query(
            Conversation,
            Customer,
            latest.c.last_time,
            latest.c.total
        )
        .join(latest, (Conversation.customer_id == latest.c.customer_id) &
                      (Conversation.created_at == latest.c.last_time))
        .join(Customer, Customer.id == Conversation.customer_id)
        .filter(Conversation.business_id == business_id)
        .order_by(latest.c.last_time.desc())
        .all()
    )
    
    return[
        {
            "customer_id": customer.id,
            "customer_phone": customer.phone_number,
            "customer_name": customer.name,
            "last_message": conv.content,
            "last_message_time": last_time,
            "total_messages": total,
        }
        for conv, customer, last_time,total in rows
    ]
    
def get_thread(db: Session, customer_id: uuid.UUID, business_id: uuid.UUID):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        return None

    messages = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.business_id == business_id,
        )
        .order_by(Conversation.created_at.asc())
        .all()
    )

    # Pull real handover status from conversation_states table
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, business_id=business_id)
        .first()
    )
    conversation_status = state.status.value if state else HandoverStatus.AI_ACTIVE.value

    return {
        "customer_id":          customer.id,
        "customer_phone":       customer.phone_number,
        "customer_name":        customer.name,
        "conversation_status":  conversation_status,
        "messages": [
            {
                "id":           m.id,
                "role":         m.role.value,
                "content":      m.content,
                "language":     m.language.value,
                "created_at":   m.created_at,
                "delivery_status": m.delivery_status,
            }
            for m in messages
        ],
    }
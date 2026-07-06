"""
pure SQLAlchemy
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Conversation, Customer, ConversationState, HandoverStatus


def get_inbox(db: Session, user_id: int) -> list[dict]:
    """
    Returns one row per customer - their latest message and metadata.
    Used to render the inbox list on the dashboard.
    """
    latest = (
        db.query(
            Conversation.customer_id,
            func.max(Conversation.timestamp).label("last_time"),
            func.count(Conversation.id).label("total")
        )
        .filter(Conversation.user_id == user_id)
        .group_by(Conversation.customer_id)
        .subquery()
    )
    
    #join back to get the actual message text at that timestamp
    rows = (
        db.query(
            Conversation,
            Customer,
            latest.c.last_time,
            latest.c.total
        )
        .join(latest, (Conversation.customer_id == latest.c.customer_id) &
                      (Conversation.timestamp == latest.c.last_time))
        .join(Customer, Customer.id == Conversation.customer_id)
        .filter(Conversation.user_id == user_id)
        .order_by(latest.c.last_time.desc())
        .all()
    )
    
    #step 3 -fetch all conversation states for this business in one query-This avoids N+1 queries and join ambiguity
    states = {
        s.customer_id : s.status
        for s in db.query(ConversationState)
        .filter(ConversationState.user_id == user_id)
        .all()
    }
    
    result = []
    for conv, customer, last_time, total in rows:
        status = states.get(customer.id, HandoverStatus.ai_active)
        
        result.append(
        {
            "customer_id": customer.id,
            "customer_phone": customer.phone_number,
            "customer_name": customer.name,
            "last_message": conv.message_text,
            "last_message_time": last_time,
            "total_messages": total,
            "conversation_status": status.value,
        }     
    )
    return result
    
def get_thread(db: Session, customer_id: int, user_id: int):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id,
                Customer.user_id == user_id,
                )
        .first()
    )
    if not customer:
        return None

    messages = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.user_id == user_id,
        )
        .order_by(Conversation.timestamp.asc())
        .all()
    )

    # Pull real handover status from conversation_states table
    state = (
        db.query(ConversationState)
        .filter_by(customer_id=customer_id, user_id=user_id)
        .first()
    )
    conversation_status = state.status.value if state else HandoverStatus.ai_active.value

    return {
        "customer_id":          customer.id,
        "customer_phone":       customer.phone_number,
        "customer_name":        customer.name,
        "conversation_status":  conversation_status,
        "messages": [
            {
                "id":           m.id,
                "sender":       m.sender.value,
                "message_text": m.message_text,
                "language":     m.language.value,
                "timestamp":    m.timestamp,
                "delivery_status": m.delivery_status,
            }
            for m in messages
        ],
    }
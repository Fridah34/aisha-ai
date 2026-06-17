"""
pure SQLAlchemy
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Conversation, Customer

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
    
    return[
        {
            "customer_id": customer.id,
            "customer_phone": customer.phone_number,
            "customer_name": customer.name,
            "last_message": conv.message_text,
            "last_message_time": last_time,
            "total_messages": total,
        }
        for conv, customer, last_time,total in rows
    ]
    
def get_thread(
    db: Session,
    customer_id: int,
    user_id: int,
    limit: int = 50
) -> dict | None:
    """
    Returns the full message thread for one customer.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return None
    
    #Verify this customer has actually talked to this business
    exists = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.user_id == user_id
        )
        .first()
    )
    if not exists:
        return None
    
    messages = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.user_id == user_id
        )
        .order_by(Conversation.timestamp.asc())
        .limit(limit)
        .all()
    )
    
    return {
        "customer_id": customer.id,
        "customer_phone": customer.phone_number,
        "customer_name": customer.name,
        "messages": messages,
    }
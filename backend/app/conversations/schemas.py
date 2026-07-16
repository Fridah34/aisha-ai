"""
Pydantic schemas for the conversations API.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    """One message in a conversation thread."""
    id: uuid.UUID
    role: str
    content: str
    language: str
    created_at: datetime
    delivery_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ConversationSummary(BaseModel):
    """
    One row in the inbox list.
    Shows the customer and their most recent message —
    enough for the dashboard to render an inbox without
    fetching every message for every customer.
    """
    customer_id: uuid.UUID
    customer_phone: str
    customer_name: Optional[str]
    last_message: str
    last_message_time: datetime
    total_messages: int
    
class ConversationThread(BaseModel):
    """
    Full message thread for one customer.
    Returned by GET /conversations/{customer_id}.
    """
    customer_id: uuid.UUID
    customer_phone: str
    customer_name: Optional[str]
    conversation_status: str
    messages: list[MessageResponse]
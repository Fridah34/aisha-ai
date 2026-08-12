"""
Pydantic schemas for the conversations API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    """One message in a conversation thread."""

    id: uuid.UUID
    role: str
    content: str
    language: str
    created_at: datetime
    delivery_status: str | None = None

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
    customer_name: str | None
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
    customer_name: str | None
    conversation_status: str
    messages: list[MessageResponse]


class HandoverEventOut(BaseModel):
    """
    One AI→human escalation event, as returned by
    GET /conversations/{customer_id}/handover-history.
    resolved_at is None while the escalation is still open —
    the dashboard uses that to separate "needs attention now"
    from "already dealt with" in the same list.
    """

    id: uuid.UUID
    reason_code: str
    reason: str
    ai_summary: str | None = None
    customer_last_message: str
    created_at: datetime
    resolved_at: datetime| None = None

    model_config = ConfigDict(from_attributes=True)
    
    
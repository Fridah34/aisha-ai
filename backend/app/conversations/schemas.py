"""
Pydantic schemas for the conversations API.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageResponse(BaseModel):
    """One message in a conversation thread."""
    id: int
    sender: str
    message_text:str
    language:str
    timestamp: datetime
    delivery_status: Optional[str] = None 
    
    class Config:
        from_attributes = True
        
class ConversationSummary(BaseModel):
    """
    One row in the inbox list.
    Shows the customer and their most recent message —
    enough for the dashboard to render an inbox without
    fetching every message for every customer.
    """
    customer_id: int
    customer_phone: str
    customer_name: Optional[str]
    last_message: str
    last_message_time: datetime
    total_messages: int
    conversation_status : str
    
class ConversationThread(BaseModel):
    """
    Full message thread for one customer.
    Returned by GET /conversations/{customer_id}.
    """
    customer_id: int
    customer_phone: str
    customer_name: Optional[str]
    conversation_status: str
    messages: list[MessageResponse]
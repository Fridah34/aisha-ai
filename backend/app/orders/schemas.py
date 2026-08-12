import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import OrderStatus


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    product_name: str | None
    quantity: int
    total_amount: Decimal
    status: OrderStatus

    class Config:
        from_attributes = True


class OrderGroupResponse(BaseModel):
    """One card per WhatsApp checkout on the dashboard, even though it's
    backed by N Order rows sharing one order_group_id. Legacy rows with
    no group id (pre-migration) each render as their own single-item
    group."""

    order_ref: str
    customer_name: str | None
    customer_phone: str | None
    created_at: datetime
    total_amount: Decimal
    items: list[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus

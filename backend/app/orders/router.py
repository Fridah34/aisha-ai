"""
Orders API — lets the business owner see what's been ordered through
AISHA on WhatsApp, and update per-item fulfilment status.

AUTH: business_id comes from the authenticated session (get_current_user),
never from the client. Orders themselves are never created here — they
come exclusively from the WhatsApp checkout flow
(app.flows.marketplace_flow.create_orders_from_cart).
"""
import uuid

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.orders import crud
from app.orders.schemas import OrderGroupResponse, OrderItemResponse, OrderStatusUpdate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=list[OrderGroupResponse])
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every order for this business, grouped by WhatsApp checkout and
    sorted newest-first."""
    orders = crud.get_orders_for_business(db, current_user.id)
    groups = crud.group_orders_by_checkout(orders)

    return [
        OrderGroupResponse(
            order_ref=str(rows[0].order_group_id)[:8] if rows[0].order_group_id else str(rows[0].id),
            customer_name=rows[0].snapshot_customer_name,
            customer_phone=rows[0].snapshot_customer_phone,
            created_at=rows[0].created_at,
            total_amount=sum(r.total_amount for r in rows),
            items=[
                OrderItemResponse(
                    id=r.id,
                    product_id=r.product_id,
                    product_name=r.snapshot_product_name,
                    quantity=r.quantity,
                    total_amount=r.total_amount,
                    status=r.status,
                )
                for r in rows
            ],
        )
        for rows in groups
    ]


@router.patch("/{order_id}/status", response_model=OrderItemResponse)
def set_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates one line item's fulfilment status. Scoped to the owning
    business via get_order_by_id — a 404 (not 403) on mismatch, same
    pattern as categories/router.py, so the API doesn't confirm an
    order id exists for another business."""
    order = crud.get_order_by_id(db, order_id, current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updated = crud.update_order_status(db, order, payload.status)
    return OrderItemResponse(
        id=updated.id,
        product_id=updated.product_id,
        product_name=updated.snapshot_product_name,
        quantity=updated.quantity,
        total_amount=updated.total_amount,
        status=updated.status,
    )
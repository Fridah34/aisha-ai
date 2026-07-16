"""
Orders CRUD — all reads scoped to the authenticated business owner via
user_id, matching categories/crud.py. Grouping by order_group_id happens
here (not in the router) so it's one tested place, same reasoning as
categories/crud.py owning display_order computation.
"""
import itertools
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Order


def get_orders_for_business(db: Session, user_id: int) -> list[Order]:
    """All Order rows for one business, newest first. Grouping into
    checkouts happens in the router's response construction, not here —
    this stays a flat, simple query so it's reusable (e.g. for a future
    export/report feature) without dragging grouping logic along."""
    return (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
        .all()
    )


def group_orders_by_checkout(orders: list[Order]) -> list[list[Order]]:
    """Groups already-sorted (newest-first) Order rows by order_group_id.
    Legacy rows with order_group_id == None each become their own
    single-item group (via a synthetic per-row UUID) rather than being
    merged together or dropped — those predate the order_group_id
    migration and have no real relationship to each other."""
    def group_key(o: Order):
        return o.order_group_id or UUID(int=o.id)

    return [list(rows) for _, rows in itertools.groupby(orders, key=group_key)]


def get_order_by_id(db: Session, order_id: int, user_id: int) -> Order | None:
    """Scoped to the owning business — same pattern as
    categories/crud.get_category_by_id, so an owner can never read or
    modify another business's order by guessing an id."""
    return (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == user_id)
        .first()
    )


def update_order_status(db: Session, order: Order, status) -> Order:
    """Updates ONE line item's status, not the whole checkout group —
    items sharing an order_group_id can have independent fates (one
    shipped, one cancelled), so there's deliberately no
    update_checkout_status() bulk equivalent yet."""
    order.status = status
    db.commit()
    db.refresh(order)
    return order
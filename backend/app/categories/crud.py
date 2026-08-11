import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.categories.schemas import CategoryCreate, CategoryUpdate
from app.models import Category, Product


def get_categories_for_business(db: Session, business_id: uuid.UUID) -> list[dict]:
    """
    Returns every category for one business, ordered for display, each
    annotated with a live product_count.

    Uses a single grouped query (outerjoin + count) rather than looping
    over categories and calling len(category.products) per row — the
    same N+1 pitfall already hit and fixed once in
    conversations/crud.py's get_inbox().
    """
    rows = (
        db.query(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .filter(Category.business_id == business_id)
        .group_by(Category.id)
        .order_by(Category.display_order, Category.name)
        .all()
    )

    return [
        {
            "id": category.id,
            "business_id": category.business_id,
            "name": category.name,
            "description": category.description,
            "display_order": category.display_order,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "product_count": count,
        }
        for category, count in rows
    ]


def get_category_by_id(
    db: Session, category_id: uuid.UUID, business_id: uuid.UUID
) -> Category | None:
    """
    Fetches a single category, scoped to the owning business — same
    scoping reasoning as products/crud.py's get_product_by_id.
    """
    return (
        db.query(Category)
        .filter(Category.id == category_id, Category.business_id == business_id)
        .first()
    )


def create_category(
    db: Session, category_data: CategoryCreate, business_id: uuid.UUID
) -> Category:
    """
    Inserts a new category row for the authenticated business.
    business_id comes from the caller (the authenticated session), never
    from category_data, and display_order is always computed — new
    categories always land at the end of the list without the owner
    needing to know the current highest.
    """
    data = category_data.model_dump(
        exclude={"display_order", "business_id"}, exclude_unset=True
    )
    new_category = Category(
        **data,
        business_id=business_id,
        display_order=get_next_display_order(db, business_id),
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


def update_category(
    db: Session,
    category: Category,
    updates: CategoryUpdate,
) -> Category:
    """Applies only the fields the client actually sent, same pattern as update_product."""
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    """
    Deletes a category. Products in it are NOT deleted — category_id
    has ON DELETE SET NULL, so PostgreSQL automatically un-links them
    rather than cascading the delete.
    """
    db.delete(category)
    db.commit()


def get_next_display_order(db: Session, business_id: uuid.UUID) -> int:
    """
    Returns one more than the business's current highest display_order,
    or 0 if they have no categories yet. Same reasoning as get_inbox()'s
    fix — derive from actual DB state instead of trusting caller input.
    """
    max_order = (
        db.query(func.max(Category.display_order))
        .filter(Category.business_id == business_id)
        .scalar()
    )
    return 0 if max_order is None else max_order + 1

"""
Database operations for products — no FastAPI/HTTP concerns here.
Kept separate from router.py so these functions can be tested directly
or reused (e.g. called from a future bulk-import script) without
spinning up an HTTP request.
"""
from sqlalchemy.orm import Session
from app.models import Product
from app.products.schemas import ProductCreate, ProductUpdate


def get_products_for_business(db: Session, user_id: int) -> list[Product]:
    """Returns every product belonging to one business, newest first."""
    return (
        db.query(Product)
        .filter(Product.user_id == user_id)
        .order_by(Product.created_at.desc())
        .all()
    )


def get_product_by_id(db: Session, product_id: int, user_id: int) -> Product | None:
    """
    Fetches a single product, scoped to the owning business.
    The user_id filter is deliberate — without it, business A
    could fetch/edit business B's products by guessing IDs.
    """
    return (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user_id)
        .first()
    )


def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Inserts a new product row and returns the created object."""
    new_product = Product(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


def update_product(
    db: Session,
    product: Product,
    updates: ProductUpdate,
) -> Product:
    """
    Applies only the fields the client actually sent.
    exclude_unset=True means a field left out of the request body
    is untouched — not overwritten with None.
    """
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Permanently removes a product. No soft-delete for now —
    add a deleted_at column later if you need order history
    to still reference removed products."""
    db.delete(product)
    db.commit()
    
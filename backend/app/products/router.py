"""
Products API= lets the business owner manage their catalogue without manually inserting rows into postgreSQL.

AUTH: business_id comes from the authenticated session (get_current_user), never from the client.
"""

import os
import uuid

from app.ai.cache import invalidate_business_cache
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Product, User
from app.products import crud
from app.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/products", tags=["Products"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 2 * 1024 * 1024


@router.get("", response_model=list[ProductResponse])
def list_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns every product for one business
    """
    return crud.get_products_for_business(db, current_user.id)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns one product, scoped to the owning business."""
    product = crud.get_product_by_id(db, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new product.

    Invalidates the Redis-cached business prompt immediately —
    without this, AISHA would keep telling customers about the
    old product list for up to an hour (the cache TTL).
    """
    # Ignore any business_id the client sent — always attribute the new
    # product to the authenticated caller, never a client-supplied value.
    product_data.business_id = current_user.id
    new_product = crud.create_product(db, product_data)
    invalidate_business_cache(current_user.id)
    return new_product


@router.put("/{product_id}", response_model=ProductResponse)
def edit_product(
    product_id: uuid.UUID,
    updates: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates an existing product (price change, mark out of stock, etc).
    Invalidates the business prompt cache so AISHA reflects the
    change on the very next customer message.
    """
    product = crud.get_product_by_id(db, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated = crud.update_product(db, product, updates)
    invalidate_business_cache(current_user.id)
    return updated


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a product and invalidates the cache."""
    product = crud.get_product_by_id(db, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud.delete_product(db, product)
    invalidate_business_cache(current_user.id)
    return None


@router.post("/{product_id}/image")
async def upload_product_image(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # validate type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are allowed")

    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image must be under 2MB")

    # Optional - resize /compress with pillow if installed
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(contents))
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        fmt = "JPEG" if file.content_type == "image/jpeg" else "PNG"
        img.save(buf, format=fmt, optimize=True, quality=85)
        contents = buf.getvalue()
    except ImportError:
        pass

    # save to disk
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = f"uploads/products/{current_user.id}"
    os.makedirs(folder, exist_ok=True)
    filepath = f"{folder}/{filename}"

    with open(filepath, "wb") as f:
        f.write(contents)

    # Save URL to DB
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.business_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(404, "Product not found")

    product.image_url = f"/{filepath}"
    db.commit()

    return {"image_url": f"/{filepath}"}

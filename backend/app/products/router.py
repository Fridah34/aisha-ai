"""
Products API= lets the business owner manage their catalogue without manually inserting rows into postgreSQL.

AUTH NOTE:user_id is currently passed explicitly by the caller.

"""
from fastapi import APIRouter, Depends,HTTPException,status
from sqlalchemy.orm import Session

from app.database import get_db
from app.products import crud
from app.products.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.ai.cache import invalidate_business_cache

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=list[ProductResponse])
def list_products(user_id: int, db: Session = Depends(get_db)):
    """
    Returns every product for one business
    """
    return crud.get_products_for_business(db, user_id)

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, user_id: int, db: Session = Depends(get_db)):
    """Returns one product, scoped to the owning business."""
    product = crud.get_product_by_id(db, product_id, user_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
 
 
@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """
    Creates a new product.
 
    Invalidates the Redis-cached business prompt immediately —
    without this, AISHA would keep telling customers about the
    old product list for up to an hour (the cache TTL).
    """
    new_product = crud.create_product(db, product_data)
    invalidate_business_cache(product_data.user_id)
    return new_product
 
 
@router.put("/{product_id}", response_model=ProductResponse)
def edit_product(
    product_id: int,
    user_id: int,
    updates: ProductUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates an existing product (price change, mark out of stock, etc).
    Invalidates the business prompt cache so AISHA reflects the
    change on the very next customer message.
    """
    product = crud.get_product_by_id(db, product_id, user_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
 
    updated = crud.update_product(db, product, updates)
    invalidate_business_cache(user_id)
    return updated
 
 
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product(product_id: int, user_id: int, db: Session = Depends(get_db)):
    """Deletes a product and invalidates the cache."""
    product = crud.get_product_by_id(db, product_id, user_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
 
    crud.delete_product(db, product)
    invalidate_business_cache(user_id)
    return None
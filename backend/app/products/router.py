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
from app.models import Product 

import uuid
import os
from fastapi import UploadFile, File

router = APIRouter(prefix="/products", tags=["Products"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 2 * 1024 * 1024

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

@router.post("/{product_id}/image")
async def upload_product_image(
    product_id : int,
    user_id : int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    #validate type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are allowed")
    
    #Read and validate size
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image must be under 2MB")
    
    #Optional - resize /compress with pillow if installed
    try: 
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(contents))
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        fmt = "JPEG" if file.content_type == "image/jpeg" else "PNG"
        img.save(buf, format=fmt, optimize= True, quality=85)
        contents = buf.getvalue()
    except ImportError:
        pass
    
    #save to disk
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{product_id}_ {uuid.uuid4().hex[:8]}.{ext}"
    folder = f"uploads/products/{user_id}"
    os.makedirs(folder, exist_ok=True)
    filepath = f"{folder}/{filename}"
    
    with open(filepath, "wb") as f:
        f.write(contents)
        
    #Save URL to DB
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == user_id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    product.image_url = f"/{filepath}"
    db.commit()
    
    return {"image_url": f"/{filepath}"}
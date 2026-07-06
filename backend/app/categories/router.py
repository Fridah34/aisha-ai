"""
Categories API — lets the business owner group products into categories
that AISHA presents to WhatsApp customers as a browsable list.

AUTH NOTE: user_id is currently passed explicitly by the caller, same
placeholder pattern as products/router.py until Eve's JWT lands.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.categories import crud
from app.categories.schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from app.ai.cache import invalidate_business_cache

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(user_id: int, db: Session = Depends(get_db)):
    """Returns every category for one business, with a live product count."""
    return crud.get_categories_for_business(db, user_id)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, user_id: int, db: Session = Depends(get_db)):
    """Returns one category, scoped to the owning business."""
    category = crud.get_category_by_id(db, category_id, user_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(category_data: CategoryCreate, db: Session = Depends(get_db)):
    """
    Creates a new category.

    Invalidates the business prompt cache — product data (which the
    prompt does reference) is expected to start changing alongside
    category assignments, so this keeps the cache honest going forward.
    """
    try:
        new_category = crud.create_category(db, category_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists for this business.",
        )
    invalidate_business_cache(category_data.user_id)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
def edit_category(
    category_id: int,
    user_id: int,
    updates: CategoryUpdate,
    db: Session = Depends(get_db),
):
    """Updates an existing category (rename, reorder, activate/deactivate)."""
    category = crud.get_category_by_id(db, category_id, user_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        updated = crud.update_category(db, category, updates)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists for this business.",
        )
    invalidate_business_cache(user_id)
    return updated


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(category_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Deletes a category. Products in it are NOT deleted — category_id
    is ON DELETE SET NULL, so they simply become uncategorized.
    """
    category = crud.get_category_by_id(db, category_id, user_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    crud.delete_category(db, category)
    invalidate_business_cache(user_id)
    return None

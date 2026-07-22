"""
Categories API — lets the business owner group products into categories
that AISHA presents to WhatsApp customers as a browsable list.

AUTH: business_id comes from the authenticated session (get_current_user), never from the client.
"""

import uuid

from app.ai.cache import invalidate_business_cache
from app.auth.dependencies import get_current_user
from app.categories import crud
from app.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.database import get_db
from app.models import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns every category for one business, with a live product count."""
    return crud.get_categories_for_business(db, current_user.id)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns one category, scoped to the owning business."""
    category = crud.get_category_by_id(db, category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new category. display_order is computed automatically —
    the new category is placed after the current highest order for
    this business, so the caller never needs to supply it.
    """
    try:
        new_category = crud.create_category(db, category_data, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists for this business.",
        )
    invalidate_business_cache(current_user.id)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
def edit_category(
    category_id: uuid.UUID,
    updates: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates an existing category (rename, reorder, activate/deactivate)."""
    category = crud.get_category_by_id(db, category_id, current_user.id)
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
    invalidate_business_cache(current_user.id)
    return updated


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes a category. Products in it are NOT deleted — category_id
    is ON DELETE SET NULL, so they simply become uncategorized.
    """
    category = crud.get_category_by_id(db, category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    crud.delete_category(db, category)
    invalidate_business_cache(current_user.id)
    return None

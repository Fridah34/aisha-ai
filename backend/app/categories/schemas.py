"""
Pydantic schemas for the Categories API

Same separation as products/schemas.py: the DB model defines storage,
these schemas define the API contract.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """
    What we send back to the client. product_count is not a database
    column — it's computed in crud.get_categories_for_business() via a
    grouped query and attached at read time. It defaults to None on
    single-item responses (create/update/get-by-id), where a live count
    isn't computed since only the list endpoint needs it for display.
    """
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    product_count: Optional[int] = None

    class Config:
        from_attributes = True
"""
Pydantic schemas for the Products API

The Db model defines storage. These schemas define the API contract-what a client is allowed to send,and what we choose to send back.
Keeping them separate means we can change the Db without breaking the API, and vice versa.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    # business_id is deliberately NOT part of this schema — it's never
    # sent by the client. The router injects it from the authenticated
    # user before the product is persisted (see products/router.py).
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    is_available: bool = True
    category_id: Optional[uuid.UUID] =None 
    variant_label: Optional[str] = None
    variant_options: Optional[str] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    upsell_text: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    is_available: Optional[bool] = None
    category_id: Optional[uuid.UUID] = None
    variant_label: Optional[str] = None
    variant_options: Optional[str] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    upsell_text: Optional[str] = None


class ProductResponse(BaseModel):
    """
    What we send back to the client. Includes DB-generated fields
    (id, timestamps) that the client never sends us.
    """

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    is_available: bool
    category_id: Optional[uuid.UUID] = None
    variant_label: Optional[str] = None
    variant_options: Optional[str] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    upsell_text: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True
    )  # allows .model_validate() / direct model -> schema conversion

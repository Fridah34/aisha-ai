"""
Settings API — lets the business owner update their knowledge base
and business type from the dashboard.

These two fields directly control how AISHA behaves:
- knowledge_base_text: injected into every prompt as business context
- business_type: selects the action flow (retail / services / general)

AUTH: user_id now comes from the authenticated session (get_current_user),
never from the client.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.auth.dependencies import get_current_user
from app.ai.cache import invalidate_business_cache

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    knowledge_base_text: Optional[str] = None
    business_type: Optional[str] = None  # "retail" | "services" | "general"


class SettingsResponse(BaseModel):
    id: int
    business_name: str
    knowledge_base_text: Optional[str]
    business_type: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=SettingsResponse)
def get_settings(current_user: User = Depends(get_current_user)):
    """Returns current settings for the authenticated business."""
    return current_user


@router.patch("", response_model=SettingsResponse)
def update_settings(
    updates: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates knowledge base and/or business type.
    Immediately invalidates the Redis prompt cache so AISHA
    reflects the changes on the very next customer message.

    PATCH not PUT — only the fields sent are updated,
    everything else is left untouched.
    """
    if updates.knowledge_base_text is not None:
        current_user.knowledge_base_text = updates.knowledge_base_text

    if updates.business_type is not None:
        valid_types = {"retail", "services", "general"}
        if updates.business_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"business_type must be one of: {valid_types}"
            )
        current_user.business_type = updates.business_type

    db.commit()
    db.refresh(current_user)

    invalidate_business_cache(current_user.id)

    return current_user
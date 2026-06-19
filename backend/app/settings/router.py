"""
Settings API — lets the business owner update their knowledge base
and business type from the dashboard.

These two fields directly control how AISHA behaves:
- knowledge_base_text: injected into every prompt as business context
- business_type: selects the action flow (retail / services / general)

AUTH NOTE: user_id passed explicitly for now.
Replace with Depends(get_current_user) when Eve's JWT auth is ready.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
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
def get_settings(user_id: int, db: Session = Depends(get_db)):
    """Returns current settings for the business."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Business not found")
    return user


@router.patch("", response_model=SettingsResponse)
def update_settings(
    user_id: int,
    updates: SettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates knowledge base and/or business type.
    Immediately invalidates the Redis prompt cache so AISHA
    reflects the changes on the very next customer message.

    PATCH not PUT — only the fields sent are updated,
    everything else is left untouched.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Business not found")

    if updates.knowledge_base_text is not None:
        user.knowledge_base_text = updates.knowledge_base_text

    if updates.business_type is not None:
        valid_types = {"retail", "services", "general"}
        if updates.business_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"business_type must be one of: {valid_types}"
            )
        user.business_type = updates.business_type

    db.commit()
    db.refresh(user)

    # Invalidate cache — AISHA rebuilds prompt on next message
    invalidate_business_cache(user_id)

    return user
"""
Settings API — lets the business owner update their knowledge base
and business type from the dashboard.

These two fields directly control how AISHA behaves:
- knowledge_base_text: injected into every prompt as business context
- business_type: selects the action flow (retail / services / general)

AUTH: business_id comes from the authenticated session (get_current_user), never from the client.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.cache import invalidate_business_cache
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.handover.schemas import (
    HandoverNotificationSettings,
    HandoverNotificationSettingsUpdate,
)
from app.models import DEFAULT_HANDOVER_NOTIFICATIONS, User

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    knowledge_base_text: str | None = None
    business_type: str | None = None  # "retail" | "services" | "general"
    delivery_location: str | None = None
    handover_notifications: HandoverNotificationSettingsUpdate | None = None


class SettingsResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    knowledge_base_text: str | None
    business_type: str | None
    delivery_location: str | None
    handover_notifications: HandoverNotificationSettings

    class Config:
        from_attributes = True


@router.get("", response_model=SettingsResponse)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns current settings for the business."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Business not found")
    return user


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
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Business not found")

    if updates.knowledge_base_text is not None:
        user.knowledge_base_text = updates.knowledge_base_text

    if updates.delivery_location is not None:
        user.delivery_location = updates.delivery_location

    if updates.business_type is not None:
        valid_types = {"retail", "services", "general"}
        if updates.business_type not in valid_types:
            raise HTTPException(
                status_code=400, detail=f"business_type must be one of: {valid_types}"
            )
        user.business_type = updates.business_type

    if updates.handover_notifications is not None:
        # Merge — a partial update (e.g. only `whatsapp`) must never wipe out
        # the other channels' previously saved settings.
        merged = {
            **DEFAULT_HANDOVER_NOTIFICATIONS,
            **(user.handover_notifications or {}),
        }
        incoming = updates.handover_notifications.model_dump(exclude_none=True)
        for channel, channel_settings in incoming.items():
            merged[channel] = channel_settings
        user.handover_notifications = merged

    db.commit()
    db.refresh(user)

    # Invalidate cache — AISHA rebuilds prompt on next message
    invalidate_business_cache(current_user.id)

    return user

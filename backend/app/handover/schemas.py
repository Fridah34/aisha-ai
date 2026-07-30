"""
Pydantic schemas for the Human Handover Notification system.

`HandoverChannelSettings`/`HandoverNotificationSettings` describe the
business-configurable notification rules (persisted as JSON on
`User.handover_notifications` — see app/models.py). `NotificationPayload` is
the single shape every channel notifier (Dashboard/WhatsApp/Email) receives;
new channels reuse the exact same payload, they never invent their own.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models import HandoverEventStatus, HandoverReasonCode
from pydantic import BaseModel, ConfigDict, Field


class HandoverChannelSettings(BaseModel):
    """One channel's notification rule: on/off + how long to wait before
    firing. `delay_minutes == 0` means "immediately"."""

    enabled: bool = True
    delay_minutes: int = Field(default=0, ge=0, le=120)


class HandoverNotificationSettings(BaseModel):
    """The full `handover_notifications` JSON blob. Adding a future channel
    (SMS, Slack, Teams, Telegram, push) means adding one more optional field
    here — the notification engine itself never needs to change."""

    dashboard: HandoverChannelSettings = Field(default_factory=HandoverChannelSettings)
    whatsapp: HandoverChannelSettings = Field(default_factory=HandoverChannelSettings)
    email: HandoverChannelSettings = Field(
        default_factory=lambda: HandoverChannelSettings(enabled=True, delay_minutes=5)
    )


class HandoverNotificationSettingsUpdate(BaseModel):
    """PATCH-shaped counterpart of `HandoverNotificationSettings` — every
    channel is optional and left `None` when the caller doesn't send it, so
    a partial update (e.g. only `whatsapp`) never clobbers the other
    channels' saved settings."""

    dashboard: HandoverChannelSettings | None = None
    whatsapp: HandoverChannelSettings | None = None
    email: HandoverChannelSettings | None = None


class NotificationPayload(BaseModel):
    """Reused by every channel notifier — Dashboard, WhatsApp, Email, and any
    future channel. Built once per `HandoverEvent` by `NotificationService`."""

    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    conversation_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None
    customer_phone: str
    reason_code: HandoverReasonCode
    reason: str
    reason_label: str
    ai_summary: str | None
    customer_last_message: str
    waiting_start_time: datetime
    waiting_time_label: str
    status: HandoverEventStatus
    # Where the business owner should be reached on each outbound channel —
    # resolved once from the business's own account data (User.email /
    # User.whatsapp_phone_number) when the payload is built, so individual
    # notifiers never need their own DB lookups.
    business_notification_email: list[str] | None = None
    business_notification_phone: str | None = None

class HandoverEventResponse(BaseModel):
    """Read-model for a `HandoverEvent` row, including the dynamically
    computed waiting duration (never stored) and the human-readable reason
    label the frontend should display instead of the raw reason code."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    conversation_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None
    customer_phone: str
    reason_code: HandoverReasonCode
    reason_label: str
    reason: str
    ai_summary: str | None
    customer_last_message: str
    waiting_start_time: datetime
    waiting_time_label: str
    status: HandoverEventStatus
    created_at: datetime
    updated_at: datetime

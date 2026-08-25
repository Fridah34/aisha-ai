"""Notifier abstraction — every channel (Dashboard, WhatsApp, Email, and any
future SMS/Slack/Teams/Telegram/push channel) implements this same
interface. The notification engine (NotificationService/NotificationScheduler)
only ever calls `send()` — it never knows how a channel actually delivers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.handover.schemas import NotificationPayload


class Notifier(ABC):
    """Base class for a single notification channel."""

    #: Matches the channel key used in `User.handover_notifications`
    #: (e.g. "dashboard", "whatsapp", "email").
    channel_key: str

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Delivers the notification. Returns True on success, False on a
        handled failure (never raises for expected delivery failures —
        mirrors the rest of the codebase's `send_text_message() -> bool`
        pattern)."""
        raise NotImplementedError

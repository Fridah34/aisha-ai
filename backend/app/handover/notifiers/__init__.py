from app.handover.notifiers.base import Notifier
from app.handover.notifiers.dashboard import DashboardNotifier
from app.handover.notifiers.email import EmailNotifier
from app.handover.notifiers.whatsapp import WhatsAppNotifier

#: Registry the notification engine iterates over. Adding a future channel
#: (SMS, Slack, Teams, Telegram, push) means writing one more `Notifier`
#: subclass and adding it here — nothing else in the engine changes.
NOTIFIERS: dict[str, Notifier] = {
    DashboardNotifier.channel_key: DashboardNotifier(),
    WhatsAppNotifier.channel_key: WhatsAppNotifier(),
    EmailNotifier.channel_key: EmailNotifier(),
}

__all__ = ["NOTIFIERS", "DashboardNotifier", "EmailNotifier", "Notifier", "WhatsAppNotifier"]

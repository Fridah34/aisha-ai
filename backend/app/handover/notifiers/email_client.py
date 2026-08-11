"""Email delivery client.

No email provider/library (SMTP, SendGrid, SES, etc.) or credentials exist
anywhere in this project yet (checked app/config.py, requirements.txt). This
client is a clean, honest boundary for that future integration: it does not
fabricate a successful send. `EmailNotifier` calls this, logs clearly that
email is not configured, and returns False rather than silently pretending
to deliver.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """No email provider is wired up yet. Flip this once one is added
    (e.g. an EMAIL_* block in app/config.py)."""
    return False


def send_email(*, to_address: str, subject: str, body: str) -> bool:
    """Placeholder boundary for a real email provider integration.

    Intentionally raises rather than pretending to send, so a future
    integrator cannot accidentally ship this as "working" — callers should
    check `is_configured()` first (EmailNotifier already does this).
    """
    raise NotImplementedError(
        "Email delivery is not configured. Wire a provider (SMTP/SendGrid/SES) "
        "into app/handover/notifiers/email_client.py before enabling this channel."
    )

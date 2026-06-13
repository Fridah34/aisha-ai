# app/whatsapp/parser.py


def extract_message_data(body: dict) -> dict | None:
    """
    Pulls the fields we need from Meta's webhook payload.

    Why a separate parser?
    Meta's payload structure is 6 levels deep. Putting this logic
    directly in the router makes it unreadable and untestable.
    Isolating it here means you can unit test it with raw JSON
    without spinning up a server.

    Returns a flat dict with everything the router needs, or None
    if the payload is not a standard text message (e.g. status
    updates, read receipts, voice notes — we skip those).

    """
    try:
        entry = body["entry"][0]
        change = entry["changes"][0]["value"]

        # Meta sends status updates (delivered, read) through the same
        # webhook URL. These have no "messages" key — skip them.
        if "messages" not in change:
            return None

        message = change["messages"][0]

        # Only handle text messages for now.
        # Voice notes, images, stickers etc. will be handled in version 2.
        if message.get("type") != "text":
            return {
                "phone_number": message["from"],
                "message_text": None,   # signal to router to send unsupported-type reply
                "phone_number_id": change["metadata"]["phone_number_id"],
                "customer_name": _extract_name(change),
                "message_type": message.get("type", "unknown"),
            }

        return {
            "phone_number": message["from"],
            "message_text": message["text"]["body"],
            "phone_number_id": change["metadata"]["phone_number_id"],
            "customer_name": _extract_name(change),
            "message_type": "text",
        }

    except (KeyError, IndexError, TypeError):
        # Payload shape we don't recognise — skip silently
        # Meta sends many event types; we only care about messages
        return None


def _extract_name(change: dict) -> str | None:
    """Pulls the customer's WhatsApp display name if Meta includes it."""
    try:
        return change["contacts"][0]["profile"]["name"]
    except (KeyError, IndexError, TypeError):
        return None
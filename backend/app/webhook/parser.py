def extract_message_data(form: dict) -> dict | None:
    """
    Pulls the fields we need from Twilio's webhook form payload.

    Twilio sends form-encoded data (not JSON) with these fields:
        From        = "whatsapp:+254712345678"
        To          = "whatsapp:+14155238886"
        Body        = "Habari, mna sneakers?"
        ProfileName = "Fridah"
        NumMedia    = "0"

    Returns a flat dict the router needs, or None if we should ignore
    the event (status callbacks, media-only messages, missing fields).
    """
    # Ignore Twilio status callbacks — they have MessageStatus but no Body
    if "MessageStatus" in form and "Body" not in form:
        return None

    if "MessageStatus" in form and "Body" not in form:
        return None

    try:
        from_raw = form.get("From", "")
        to_raw   = form.get("To", "")
        body     = form.get("Body", "").strip()

        if not from_raw or not to_raw:
            return None

        # Strip "whatsapp:" prefix to get plain phone numbers
        phone_number  = from_raw.replace("whatsapp:", "").strip()
        twilio_number = to_raw.replace("whatsapp:", "").strip()

        num_media = int(form.get("NumMedia", "0") or "0")

        # Media message (image, voice note, sticker) with no text
        if num_media > 0 and not body:
            return {
                "phone_number":  phone_number,
                "message_text":  None,
                "twilio_number": twilio_number,
                "customer_name": form.get("ProfileName"),
                "message_type":  "media",
            }

        # Empty body with no media — unknown event, ignore
        if not body:
            return None

        return {
            "phone_number":  phone_number,
            "message_text":  body,
            "twilio_number": twilio_number,
            "customer_name": form.get("ProfileName"),
            "message_type":  "text",
        }

    except (KeyError, ValueError, TypeError) as e:
        print(f"[Parser] Failed to parse Twilio payload: {e}")
        return None
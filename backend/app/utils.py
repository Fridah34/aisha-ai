# app/utils.py
import phonenumbers


def to_e164(raw_number: str, default_region: str = "KE") -> str | None:
    """Normalize a phone number to E.164 (+254...). Returns None if unparseable."""
    try:
        parsed = phonenumbers.parse(raw_number, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None

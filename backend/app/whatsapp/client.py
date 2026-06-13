import os
import httpx
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"

def _get_headers() -> dict:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    if not token:
        raise ValueError("WHATSAPP_ACCESS_TOKEN not set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
def send_text_message(to_phone: str, message: str, phone_number_id:str) -> bool:
    """
    Sends a plain text WhatsApp message to a customer.

    Why httpx and not requests?
    httpx supports both sync and async. FastAPI is async-first,
    and this keeps the door open for making webhook handlers async
    later without changing this function.
    """
    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=_get_headers())
            response.raise_for_status()
            print(f"[WhatsApp] Message sent to {to_phone}")
            return True

    except httpx.HTTPStatusError as e:
        print(f"[WhatsApp] API error {e.response.status_code}: {e.response.text}")
        return False

    except httpx.RequestError as e:
        print(f"[WhatsApp] Network error: {e}")
        return False


def send_owner_alert(
    owner_phone: str,
    customer_phone: str,
    customer_message: str,
    urgency: str,
    phone_number_id: str,
) -> bool:
    """
    Notifies the business owner when a handover is triggered.
    Sends a formatted alert to the owner's WhatsApp number.
    """

    alert = (
        f"A customer needs your personal attention.\n\n"
        f"*Customer:* {customer_phone}\n"
        f"*Their message:* {customer_message[:200]}\n\n"
        f"Reply to them directly on WhatsApp."
    )

    return send_text_message(owner_phone, alert, phone_number_id)
    
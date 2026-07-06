import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")


def _get_client() -> Client:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise ValueError("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set in .env")
    return Client(sid, token)
    
    
def send_text_message(to_phone: str, message: str, media_url:str =None) -> bool:
    """
    Sends a plain text WhatsApp message to a customer.

    Why httpx and not requests?
    httpx supports both sync and async. FastAPI is async-first,
    and this keeps the door open for making webhook handlers async
    later without changing this function.
    """
    try:
        client = _get_client()
        from_number = TWILIO_WHATSAPP_NUMBER or ""

        if not from_number:
            print("[Twilio] TWILIO_WHATSAPP_NUMBER not set in .env")
            return False
        
        params = {
           "from_": f"whatsapp:{from_number}",
            "to" : f"whatsapp:{to_phone}",
            "body" :message,
        }
        
        if media_url:
            params["media_url"]= [media_url]
            print(f"[TWILIO] Sending with image: {media_url}")
        
        msg = client.messages.create(**params)
        print(f"[TWILIO] Sent to {to_phone} - SID: {msg.sid}")
        return True

    except TwilioRestException as e:
        print(f"[Twilio] API error {e.code}: {e.msg}")
        return False

    except Exception as e:
        print(f"[Twilio] Unexpected error: {e}")
        return False


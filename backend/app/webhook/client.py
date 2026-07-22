import os
import json
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_LIST_PICKER_SID = os.getenv("TWILIO_LIST_PICKER_SID")
TWILIO_QUICK_REPLY_SID = os.getenv("TWILIO_QUICK_REPLY_SID")
TWILIO_BROWSE_MORE_SID = os.getenv("TWILIO_BROWSE_MORE_SID")


def _get_client() -> Client:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise ValueError("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set in .env")
    return Client(sid, token)


def send_text_message(to_phone: str, message: str, media_url: str = None) -> bool:
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
            "to": f"whatsapp:{to_phone}",
            "body": message,
        }

        if media_url:
            params["media_url"] = [media_url]
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


def send_list_picker(to_phone: str, body_text: str, items: list[str]) -> bool:
    """
    Sends a tappable list-picker menu(up to 10 items) using the aisha_list_menu_fridah template. `items` should be plain labels
    e.g. ["Dress", "Jeans", "Shawl"] - the template's {{2}}..{{11}}
    variables are filled positionally, so items[0] becomes {{2}}
    (opt_1), items[1] becomes {{3}} (opt_2), and so on.

    Twilio's list-picker template requires exactly 10 item variables
    to have been defined at creation time — if you send fewer than 10
    real items, the leftover {{N}} slots are filled with a single
    space so the message still renders instead of erroring on a
    missing variable.
    """
    if not TWILIO_LIST_PICKER_SID:
        print("[Twilio] TWILIO_LIST_PICKER_SID not set in .env")
        return False
    if len(items) > 10:
        print("[Twilio] send_list_picker: got more than 10 items, truncating")
        items = items[:10]

    try:
        client = _get_client()
        from_number = TWILIO_WHATSAPP_NUMBER or ""

        if not from_number:
            print("[Twilio] TWILIO_WHATSAPP_NUMBER not set in .env")
            return False

        content_variables = {"1": body_text}
        for i in range(10):
            content_variables[str(i + 2)] = items[i] if i < len(items) else " "
            
        print(f"[DEBUG] content_sid={TWILIO_LIST_PICKER_SID}")
        print(f"[DEBUG] content_variables={json.dumps(content_variables, indent=2)}")

        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_phone}",
            content_sid=TWILIO_LIST_PICKER_SID,
            content_variables=json.dumps(content_variables),
        )
        print(f"[TWILIO] Sent list picker to {to_phone} - SID: {msg.sid}")
        return True

    except TwilioRestException as e:
        print(f"[Twilio] API error {e.code}: {e.msg}")
        return False

    except Exception as e:
        print(f"[Twilio] Unexpected error: {e}")
        return False


def send_quick_reply(to_phone: str, body_text: str) -> bool:
    """
    Sends the Checkout / Add More quick-reply buttons using the
    aisha_cart_action_fridah template. Only {{1}} (the body text) is
    variable — the button labels/ids (checkout, add_more) were fixed
    at template-creation time, so there's nothing else to pass here.
    """
    if not TWILIO_QUICK_REPLY_SID:
        print("[Twilio] TWILIO_QUICK_REPLY_SID not set in .env")
        return False

    try:
        client = _get_client()
        from_number = TWILIO_WHATSAPP_NUMBER or ""

        if not from_number:
            print("[Twilio] TWILIO_WHATSAPP_NUMBER not set in .env")
            return False

        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_phone}",
            content_sid=TWILIO_QUICK_REPLY_SID,
            content_variables=json.dumps({"1": body_text}),
        )
        print(f"[TWILIO] Sent quick reply to {to_phone} - SID: {msg.sid}")
        return True

    except TwilioRestException as e:
        print(f"[Twilio] API error {e.code}: {e.msg}")
        return False

    except Exception as e:
        print(f"[Twilio] Unexpected error: {e}")
        return False


def send_browse_more_prompt(to_phone: str, body_text: str) -> bool:
    """
    Sends the post-checkout 'Browse more' quick-reply button using the
    aisha_post_checkout_fridah template. Only {{1}} (the body text) is
    variable — the single button's label/id ("Browse more" / browse_more)
    was fixed at template-creation time.

    Falls back to plain text with a 'menu' hint if TWILIO_BROWSE_MORE_SID
    isn't set, so a missing/misconfigured template never silently drops
    the order confirmation — the customer always hears back either way.
    """
    if not TWILIO_BROWSE_MORE_SID:
        print("[Twilio] TWILIO_BROWSE_MORE_SID not set in .env — falling back to text")
        return send_text_message(
            to_phone,
            body_text + "\n\nReply 'menu' to see our other categories! 🛍️",
        )

    try:
        client = _get_client()
        from_number = TWILIO_WHATSAPP_NUMBER or ""

        if not from_number:
            print("[Twilio] TWILIO_WHATSAPP_NUMBER not set in .env")
            return False

        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_phone}",
            content_sid=TWILIO_BROWSE_MORE_SID,
            content_variables=json.dumps({"1": body_text}),
        )
        print(f"[TWILIO] Sent browse-more prompt to {to_phone} - SID: {msg.sid}")
        return True

    except TwilioRestException as e:
        print(f"[Twilio] API error {e.code}: {e.msg}")
        return False

    except Exception as e:
        print(f"[Twilio] Unexpected error: {e}")
        return False

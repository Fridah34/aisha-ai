"""
It's a one-time setup script-creates AISHA's whatsapp content templates via Twilio's
Content API.Run this manually whenever you need to create or recreate a template shape.Not part of the live webhook/request path.

Usage: python scripts/create_templates.py
"""

import requests
import os
import json
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

if not ACCOUNT_SID or not AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env ")

CONTENT_API_URL = "https://content.twilio.com/v1/Content"


def create_list_picker_template():
    """Reusable for BOTH the category menu and stire list-same shape
    (a body message + up to 10 tappable items), different content filled
    in at the send-time via content_variables. {{1}} is the body text itself,
    {{2}} through {{11}} are up to 10 list items."""
    payload = {
        "friendly_name": "aisha_list_menu_fridah",
        "language": "en",
        "variables": {str(i): f"sample_{i}" for i in range(1, 12)},
        "types": {
            "twilio/list-picker": {
                "body": "{{1}}",
                "button": "View Options",
                "items": [
                    {"item": f"{{{{{i}}}}}", "id": f"opt_{i - 1}"} for i in range(2, 12)
                ],
            }
        },
    }
    response = requests.post(
        CONTENT_API_URL,
        auth=(ACCOUNT_SID, AUTH_TOKEN),
        json=payload,
    )
    data = response.json()
    print("\n=== LIST PICKER TEMPLATE ===")
    print(json.dumps(data, indent=2))
    return data.get("sid")


def create_quick_reply_template():
    """2 buttons for the awaiting_cart_action step: Checkout / Add More.
    Well within the 3-button in-session limit, so this never needs
    WhatsApp approval to send."""
    payload = {
        "friendly_name": "aisha_cart_action_fridah",
        "language": "en",
        "variables": {"1": "sample body text"},
        "types": {
            "twilio/quick-reply": {
                "body": "{{1}}",
                "actions": [
                    {"title": "Checkout", "id": "checkout"},
                    {"title": "Add More", "id": "add_more"},
                ],
            }
        },
    }
    response = requests.post(
        CONTENT_API_URL,
        auth=(ACCOUNT_SID, AUTH_TOKEN),
        json=payload,
    )
    data = response.json()
    print("\n=== QUICK REPLY TEMPLATE ===")
    print(json.dumps(data, indent=2))
    return data.get("sid")


def create_browse_more_template():
    """Post-checkout Quick Reply template. Confirmed via direct A/B
    testing that single-button twilio/quick-reply templates do not
    round-trip taps back to the webhook on this sandbox number — tested
    with two different button ids (browse_more, see_more_items), both
    failed identically. A 2-button version round-trips reliably. Pairs
    Browse more with Track order, which reuses existing (previously
    unwired) helpers in marketplace_flow.py."""
    payload = {
        "friendly_name": "aisha_post_checkout_fridah",
        "language": "en",
        "variables": {"1": "sample order confirmation text"},
        "types": {
            "twilio/quick-reply": {
                "body": "{{1}}",
                "actions": [
                    {"title": "Browse more", "id": "browse_more"},
                    {"title": "Track order", "id": "track_order"},
                ],
            }
        },
    }
    response = requests.post(CONTENT_API_URL, auth=(ACCOUNT_SID, AUTH_TOKEN), json=payload)
    data = response.json()
    print("\n=== BROWSE MORE TEMPLATE ===")
    print(json.dumps(data, indent=2))
    return data.get("sid")


if __name__ == "__main__":
    #list_sid = create_list_picker_template()
    #quick_reply_sid = create_quick_reply_template()
    browse_more_sid = create_browse_more_template()

    print("\n\n=== SAVE THESE TO YOUR .env ===")
    #print(f"TWILIO_LIST_PICKER_SID={list_sid}")
    #print(f"TWILIO_QUICK_REPLY_SID={quick_reply_sid}")
    print(f"TWILIO_BROWSE_MORE_SID={browse_more_sid}")

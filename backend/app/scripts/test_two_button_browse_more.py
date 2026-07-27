"""
app/scripts/test_two_button_browse_more.py

Isolates whether BUTTON COUNT is the reason aisha_post_checkout_fridah
(1 button) doesn't round-trip while aisha_cart_action_fridah (2 buttons)
does — the only structural difference found so far between a working
and non-working twilio/quick-reply template.

Creates a temporary 2-button variant with the same "Browse more" action
plus a second dummy action, sends it directly (bypassing the app, same
technique as test_browse_more.py), so you can tap it and check the
Messaging log for an Incoming row.

This does NOT touch your real aisha_post_checkout_fridah template or
.env — it's a throwaway template for this one test.

Usage:
    python app/scripts/test_two_button_browse_more.py
"""

import os
import json
import requests
from twilio.rest import Client
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
CONTENT_API_URL = "https://content.twilio.com/v1/Content"

TEST_TO_NUMBER = "whatsapp:+254706040948"
TEST_FROM_NUMBER = "whatsapp:+14155238886"

if not ACCOUNT_SID or not AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env")

# ── Step 1: create the throwaway 2-button template ────────────────────────
print("=" * 70)
print("STEP 1 — Creating temporary 2-button test template")
print("=" * 70)

payload = {
    "friendly_name": "aisha_browse_more_2btn_TEST",
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
test_sid = data.get("sid")
print(json.dumps(data, indent=2))

if not test_sid:
    raise RuntimeError("Template creation failed — no SID returned. See response above.")

# ── Step 2: send it directly, same as the earlier diagnostic sends ────────
print("\n" + "=" * 70)
print("STEP 2 — Sending 2-button test template")
print("=" * 70)

client = Client(ACCOUNT_SID, AUTH_TOKEN)
message = client.messages.create(
    content_sid=test_sid,
    content_variables=json.dumps({"1": "Diagnostic test — 2-button version."}),
    to=TEST_TO_NUMBER,
    from_=TEST_FROM_NUMBER,
)

print(f"\nSent — SID: {message.sid}")
print(f"Test template SID: {test_sid}")
print("\nNow tap either button on WhatsApp and check Twilio Console → "
      "Monitor → Logs → Messaging for a new Incoming row.")
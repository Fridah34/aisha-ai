"""
app/scripts/test_fresh_button_id.py

Re-frames the earlier "1 vs 2 buttons" test based on a new observation:
within the SAME 2-button template, "Track order" (id: track_order, never
tapped before) round-tripped fine, but "Browse more" (id: browse_more,
tapped repeatedly across many earlier diagnostic sends) did not.

That points away from BUTTON COUNT and toward ID REUSE / session-level
deduplication as the real variable. This script isolates that directly:
a single-button template using a completely fresh id/title that has
never been sent in this conversation before.

Outcomes:
- If this round-trips despite being 1 button → button count was never
  the cause; something about the specific "browse_more" id being reused
  many times in this session is being deduplicated (client-side or
  Twilio-side). The real fix is likely just using a fresh id when you
  recreate aisha_post_checkout_fridah for production — no button-count
  change needed.
- If this ALSO fails despite being a fresh id → id reuse is ruled out,
  and button count (or something else 1-button-specific) is back as the
  leading theory.

Usage:
    python app/scripts/test_fresh_button_id.py
"""

import json
import os

import requests
from dotenv import find_dotenv, load_dotenv
from twilio.rest import Client

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
CONTENT_API_URL = "https://content.twilio.com/v1/Content"

TEST_TO_NUMBER = "whatsapp:+254706040948"
TEST_FROM_NUMBER = "whatsapp:+14155238886"

if not ACCOUNT_SID or not AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env")

# ── Step 1: create a single-button template with a NEVER-USED id ─────────
print("=" * 70)
print("STEP 1 — Creating single-button template with a fresh, unused id")
print("=" * 70)

payload = {
    "friendly_name": "aisha_fresh_id_TEST",
    "language": "en",
    "variables": {"1": "sample text"},
    "types": {
        "twilio/quick-reply": {
            "body": "{{1}}",
            # deliberately NOT "browse_more" — a title/id never sent before
            "actions": [{"title": "See more items", "id": "see_more_items"}],
        }
    },
}
response = requests.post(CONTENT_API_URL, auth=(ACCOUNT_SID, AUTH_TOKEN), json=payload)
data = response.json()
test_sid = data.get("sid")
print(json.dumps(data, indent=2))

if not test_sid:
    raise RuntimeError("Template creation failed — no SID returned. See response above.")

# ── Step 2: send it directly ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 2 — Sending fresh-id single-button template")
print("=" * 70)

client = Client(ACCOUNT_SID, AUTH_TOKEN)
message = client.messages.create(
    content_sid=test_sid,
    content_variables=json.dumps({"1": "Diagnostic test — fresh id, single button."}),
    to=TEST_TO_NUMBER,
    from_=TEST_FROM_NUMBER,
)

print(f"\nSent — SID: {message.sid}")
print(f"Test template SID: {test_sid}")
print("\nNow tap 'See more items' on WhatsApp and check Twilio Console → "
      "Monitor → Logs → Messaging for a new Incoming row.")
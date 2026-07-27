"""
app/scripts/test_browse_more.py

Diagnostic script — run this from the same place you ran test_quick_reply.py.

Does two things:
1. Fetches the RAW template definitions for both the working
   (aisha_cart_action_fridah) and broken (aisha_post_checkout_fridah)
   templates directly from Twilio's Content API, so we can diff them.
2. Sends the Browse More template directly to your test number,
   bypassing router.py / client.py entirely — same technique as
   test_quick_reply.py, just pointed at TWILIO_BROWSE_MORE_SID instead.

Usage:
    python app/scripts/test_browse_more.py
"""

import os
import json
import requests
from twilio.rest import Client
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
QUICK_REPLY_SID = os.getenv("TWILIO_QUICK_REPLY_SID")
BROWSE_MORE_SID = os.getenv("TWILIO_BROWSE_MORE_SID")

TEST_TO_NUMBER = "whatsapp:+254706040948"    # your test phone, from the logs
TEST_FROM_NUMBER = "whatsapp:+14155238886"   # the sandbox number

if not all([ACCOUNT_SID, AUTH_TOKEN, QUICK_REPLY_SID, BROWSE_MORE_SID]):
    raise RuntimeError(
        "Missing one of TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / "
        "TWILIO_QUICK_REPLY_SID / TWILIO_BROWSE_MORE_SID in .env"
    )

# ── Step 1: fetch and print both template definitions, side by side ──────
print("=" * 70)
print("STEP 1 — Comparing template definitions")
print("=" * 70)

for name, sid in [
    ("cart_action (WORKING)", QUICK_REPLY_SID),
    ("post_checkout (BROKEN)", BROWSE_MORE_SID),
]:
    r = requests.get(
        f"https://content.twilio.com/v1/Content/{sid}",
        auth=(ACCOUNT_SID, AUTH_TOKEN),
    )
    print(f"\n--- {name} — SID: {sid} ---")
    print(json.dumps(r.json(), indent=2))

# ── Step 2: send Browse More directly, bypassing the app entirely ────────
print("\n" + "=" * 70)
print("STEP 2 — Sending Browse More template directly")
print("=" * 70)

client = Client(ACCOUNT_SID, AUTH_TOKEN)

message = client.messages.create(
    content_sid=BROWSE_MORE_SID,
    content_variables=json.dumps({"1": "Diagnostic test — tap Browse more below."}),
    to=TEST_TO_NUMBER,
    from_=TEST_FROM_NUMBER,
)

print(f"\nSent — SID: {message.sid}")
print("\nNow tap 'Browse more' on WhatsApp and check Twilio Console → "
      "Monitor → Logs → Messaging for a new Incoming row.")
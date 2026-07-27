"""
app/scripts/check_approval_status.py

Fetches the WhatsApp approval status for both the working
(aisha_cart_action_fridah) and non-round-tripping (aisha_post_checkout_fridah)
templates. This is the one property the earlier JSON diff didn't show —
worth checking directly since these are freshly recreated templates
(new SIDs from today), not the ones inspected in the earlier session.

Usage:
    python app/scripts/check_approval_status.py
"""

import os
import json
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
QUICK_REPLY_SID = os.getenv("TWILIO_QUICK_REPLY_SID")
BROWSE_MORE_SID = os.getenv("TWILIO_BROWSE_MORE_SID")

for name, sid in [
    ("cart_action (WORKING)", QUICK_REPLY_SID),
    ("post_checkout (NOT ROUND-TRIPPING)", BROWSE_MORE_SID),
]:
    r = requests.get(
        f"https://content.twilio.com/v1/Content/{sid}/ApprovalRequests",
        auth=(ACCOUNT_SID, AUTH_TOKEN),
    )
    print(f"\n=== {name} — SID: {sid} ===")
    print(f"HTTP {r.status_code}")
    print(json.dumps(r.json(), indent=2))
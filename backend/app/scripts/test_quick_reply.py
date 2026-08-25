"""
scripts/test_quick_reply.py

One-off diagnostic: sends the already-created aisha_cart_action_fridah
quick-reply template directly to a test number, bypassing the whole
webhook/router code path. Purpose: isolate whether twilio/quick-reply
as a CONTENT TYPE round-trips on this sandbox number at all, independent
of anything in send_browse_more_prompt or router.py.

Usage: python scripts/test_quick_reply.py
"""

import os

from dotenv import find_dotenv, load_dotenv
from twilio.rest import Client

load_dotenv(find_dotenv())

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
QUICK_REPLY_SID = os.getenv("TWILIO_QUICK_REPLY_SID")

TEST_TO_NUMBER = "whatsapp:+254706040948"  # your test phone, from the logs
TEST_FROM_NUMBER = "whatsapp:+14155238886"  # the sandbox number

client = Client(ACCOUNT_SID, AUTH_TOKEN)

message = client.messages.create(
    content_sid=QUICK_REPLY_SID,
    content_variables='{"1": "Diagnostic test — tap a button below."}',
    to=TEST_TO_NUMBER,
    from_=TEST_FROM_NUMBER,
)

print(f"Sent — SID: {message.sid}")

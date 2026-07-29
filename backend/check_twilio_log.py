"""
check_twilio_log.py

One-off diagnostic for the AISHA Twilio 50/day Sandbox cap investigation
(handover doc: "still no message log pulled to distinguish webhook-retry
duplication from genuine photo-heavy usage").

Usage:
    python check_twilio_log.py

Reads TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN from .env — same credentials
app/webhook/client.py already uses — and pulls the last 24h of outbound
WhatsApp messages straight from Twilio's own Messages API. This is ground
truth: it's what Twilio's own cap counter is based on, independent of
anything your app's logs report (which only capture the *initial* API
response, not what happened to the message afterward).

What this surfaces that your app logs can't:
- status: queued / sent / delivered / undelivered / failed — a message
  that returned a SID (logged as "sent" by client.py) can still fail
  delivery later; client.py never sees that, only Twilio does.
- error_code / error_message — Twilio's own diagnostic for anything
  that failed or bounced.
- duplicate (to, body) pairs — the strongest signal for "webhook retries
  duplicating sends" vs "genuinely high usage": if the same message body
  went to the same number more than once within seconds, that's Twilio
  retrying the webhook and a second send slipping out before the first
  one's response reached Twilio.
"""

import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from dotenv import find_dotenv, load_dotenv
from twilio.rest import Client

load_dotenv(find_dotenv())

SID = os.getenv("TWILIO_ACCOUNT_SID")
TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

if not SID or not TOKEN:
    raise SystemExit("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set in .env")

client = Client(SID, TOKEN)

# Twilio's date_sent_after filter is UTC. Using a rolling 24h window
# rather than "since local midnight" sidesteps any UTC/local mismatch
# with however the Sandbox's own daily counter actually resets.
since = datetime.now(timezone.utc) - timedelta(hours=24)

print(f"Fetching messages sent after {since.isoformat()} (UTC)...\n")

messages = client.messages.list(date_sent_after=since, limit=500)
outbound = [m for m in messages if m.direction == "outbound-api"]

print(f"Total outbound messages in last 24h: {len(outbound)}\n")

status_counts = Counter(m.status for m in outbound)
print("By status:")
for status, count in status_counts.most_common():
    print(f"  {status}: {count}")
print()

failed_or_undelivered = [m for m in outbound if m.status in ("failed", "undelivered")]
if failed_or_undelivered:
    print(f"[!] {len(failed_or_undelivered)} failed/undelivered — details:")
    for m in failed_or_undelivered:
        print(
            f"  SID {m.sid} -> {m.to} | status={m.status} | "
            f"error_code={m.error_code} | error_message={m.error_message} | "
            f"sent={m.date_sent}"
        )
    print()

# Duplicate (to, body) pairs — the key check for retry-duplication.
pair_counts = Counter((m.to, m.body) for m in outbound)
duplicates = {pair: count for pair, count in pair_counts.items() if count > 1}
if duplicates:
    print(f"[!] {len(duplicates)} message(s) sent more than once with identical body:")
    for (to, body), count in duplicates.items():
        preview = (body or "")[:60].replace("\n", " ")
        print(f"  {count}x to {to} — \"{preview}...\"")
else:
    print("No duplicate (to, body) pairs found — no obvious retry-duplication.")
print()

print("All messages, chronological:")
for m in sorted(
    outbound,
    key=lambda m: m.date_sent or datetime.min.replace(tzinfo=timezone.utc),
):
    preview = (m.body or "")[:50].replace("\n", " ")
    print(f"  {m.date_sent} | {m.to} | {m.status} | \"{preview}\"")
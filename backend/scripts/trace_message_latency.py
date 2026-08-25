"""Latency trace for one WhatsApp message through the full worker path.

Read-only with respect to the customer: every Twilio sender is stubbed, so
nothing is delivered to WhatsApp. Everything else (Neon, Upstash, Groq) is the
real thing, so the numbers reflect production latency.

Instruments at the driver level rather than by hand-editing 44 print
statements: SQLAlchemy events time every statement, and Redis.execute_command
is wrapped to time every command. That catches remote calls made deep inside
helpers that no manual stopwatch would cover.

Usage:
    python scripts/trace_message_latency.py "do you have black sneakers?"
"""

import sys
import time
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(".env")

import redis  # noqa: E402
from sqlalchemy import event  # noqa: E402

import app.ai.service as ai_service  # noqa: E402
import app.flows.marketplace_flow as mflow  # noqa: E402
import app.tasks.message_processor as mp  # noqa: E402
from app.database import async_engine, sync_engine  # noqa: E402

PHONE = "+254798080246"
MESSAGE = sys.argv[1] if len(sys.argv) > 1 else "do you have black sneakers?"

sql_calls: list[tuple[float, str]] = []
redis_calls: list[tuple[float, str]] = []
twilio_calls: list[tuple[float, str]] = []


# ── SQL timing (both engines) ────────────────────────────────────────────
def _before(conn, cursor, statement, params, context, executemany):
    context._t0 = time.perf_counter()


def _after(conn, cursor, statement, params, context, executemany):
    ms = (time.perf_counter() - context._t0) * 1000
    sql_calls.append((ms, " ".join(statement.split())[:90]))


connect_calls: list[float] = []


def _pre_connect(dialect, conn_rec, cargs, cparams):
    conn_rec._t_connect = time.perf_counter()


def _post_connect(dbapi_conn, conn_rec):
    t0 = getattr(conn_rec, "_t_connect", None)
    if t0 is not None:
        connect_calls.append((time.perf_counter() - t0) * 1000)


for eng in (sync_engine, async_engine.sync_engine):
    event.listen(eng, "before_cursor_execute", _before)
    event.listen(eng, "after_cursor_execute", _after)
    event.listen(eng, "do_connect", _pre_connect)
    event.listen(eng, "connect", _post_connect)


# ── Redis timing ─────────────────────────────────────────────────────────
_orig_exec = redis.Redis.execute_command


def _timed_exec(self, *args, **kwargs):
    t = time.perf_counter()
    try:
        return _orig_exec(self, *args, **kwargs)
    finally:
        redis_calls.append(((time.perf_counter() - t) * 1000, str(args[0])))


redis.Redis.execute_command = _timed_exec


# ── Twilio stubs (nothing is actually delivered) ─────────────────────────
def _stub(name):
    def inner(*a, **kw):
        body = kw.get("message") or kw.get("body_text") or (a[1] if len(a) > 1 else "")
        twilio_calls.append((0.0, f"{name}: {str(body)[:60]}"))
        return True

    return inner


for mod, names in (
    (mp, ("send_text_message", "send_list_picker", "send_browse_more_prompt")),
    (mflow, ("send_text_message",)),
    (ai_service, ("send_text_message",)),
):
    for n in names:
        if hasattr(mod, n):
            setattr(mod, n, _stub(n))


# ── Run the real job ─────────────────────────────────────────────────────
payload = {
    "phone_number": PHONE,
    "message_text": MESSAGE,
    "customer_name": "LatencyTrace",
    "button_payload": None,
}

print(f"\n{'=' * 78}\nTRACE: {MESSAGE!r} from {PHONE}\n{'=' * 78}\n")
t_start = time.perf_counter()
mp.process_customer_message_job(payload)
total_ms = (time.perf_counter() - t_start) * 1000

# ── Report ───────────────────────────────────────────────────────────────
sql_ms = sum(m for m, _ in sql_calls)
redis_ms = sum(m for m, _ in redis_calls)

print(f"\n{'=' * 78}\nLATENCY BREAKDOWN\n{'=' * 78}")
print(f"{'TOTAL job wall time':<38} {total_ms:9.1f} ms")
print(f"{'  SQL (Neon) — ' + str(len(sql_calls)) + ' queries':<38} {sql_ms:9.1f} ms  ({sql_ms / total_ms * 100:4.1f}%)")
print(f"{'  Redis (Upstash) — ' + str(len(redis_calls)) + ' cmds':<38} {redis_ms:9.1f} ms  ({redis_ms / total_ms * 100:4.1f}%)")
print(f"{'  Everything else (incl. Groq)':<38} {total_ms - sql_ms - redis_ms:9.1f} ms")
print(f"{'  Twilio sends (STUBBED, 0 ms)':<38} {len(twilio_calls):9d} calls")

conn_ms = sum(connect_calls)
print(f"{'  DB/TLS connection setup — ' + str(len(connect_calls)) + 'x':<38} {conn_ms:9.1f} ms  (not counted in SQL above)")

print(f"\n--- Top 12 slowest SQL queries ({len(sql_calls)} total) ---")
for ms, stmt in sorted(sql_calls, reverse=True)[:12]:
    print(f"  {ms:8.1f} ms  {stmt}")

print("\n--- DUPLICATE SQL (same statement issued more than once) ---")
dup = defaultdict(lambda: [0, 0.0])
for ms, stmt in sql_calls:
    key = stmt.split(" FROM ")[-1][:60] if " FROM " in stmt else stmt[:60]
    dup[key][0] += 1
    dup[key][1] += ms
wasted = 0.0
for key, (n, ms) in sorted(dup.items(), key=lambda kv: -kv[1][1]):
    flag = "  <-- REDUNDANT" if n > 1 else ""
    if n > 1:
        wasted += ms * (n - 1) / n
    print(f"  {ms:8.1f} ms  {n:3d}x  {key}{flag}")
print(f"\n  Time spent on repeat executions of already-fetched data: ~{wasted:.0f} ms")

print(f"\n--- Redis commands grouped ({len(redis_calls)} total) ---")
agg = defaultdict(lambda: [0, 0.0])
for ms, cmd in redis_calls:
    agg[cmd][0] += 1
    agg[cmd][1] += ms
for cmd, (n, ms) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    print(f"  {ms:8.1f} ms  {n:3d}x  {cmd}")

print("\n--- Twilio sends that WOULD have gone out ---")
for _, desc in twilio_calls:
    print(f"  {desc}")
print()

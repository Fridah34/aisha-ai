import hashlib
import json
import os
import time as _time
import uuid

import redis
from dotenv import load_dotenv

load_dotenv()


# ─── CONNECTION . We initialize Redis once when the module loads Every function reuses this single connection-return None silently — the system falls back to PostgreSQL automatically
try:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if redis_url.startswith("rediss://"):
        redis_client = redis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=None)
    else:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    print("Redis Connected successfully")
    REDIS_AVAILABLE = True
except Exception as e: # noqa: BLE001
    print(f"Redis not available: {e} - running without cache")
    REDIS_AVAILABLE = False
    redis_client = None


LOCK_TTL_SECONDS = 30


# ─── PROMPT VERSIONING ─────────────────────────────────────────────────────
# Hashes the actual bytecode of build_system_prompt so any edit to that
# function automatically produces a new cache key. Old keys for the previous
# version simply become orphaned and are never read again — no manual
# `DEL business_prompt:<id>` needed after every prompt change, and no risk
# of silently serving a stale prompt for up to an hour after a code edit.
def get_prompt_version() -> str:
    """Returns an 8-char MD5 hash of the prompt builder function bytecode."""
    from app.ai.prompt_builder import build_system_prompt

    return hashlib.md5(build_system_prompt.__code__.co_code).hexdigest()[:8]


def acquire_customer_lock(
    customer_phone: str, timeout_seconds: float = 60, ttl_seconds: int = LOCK_TTL_SECONDS
) -> str | None:
    """Per-customer mutex so two jobs for the same phone number can never
    process concurrently and race on MarketplaceSession state — this is
    what actually enforces ordering, since RQ itself does not guarantee
    two jobs for the same customer run one-at-a-time if more than one
    worker process is running.

    Uses SET NX EX (atomic in Redis) so two workers picking up jobs at
    the same instant can't both believe they hold the lock.

    Blocks up to timeout_seconds, polling every 200ms, then gives up and
    returns None — the caller should treat that as "something is stuck",
    not normal contention, since 60s of a lock held straight through is
    far longer than any single message should ever take to process.

    Returns a random token (proof of ownership — release_customer_lock
    checks it, so it can never delete a DIFFERENT job's lock acquired
    after ours expired) or "no-redis" if Redis is unavailable, matching
    this file's fail-open philosophy elsewhere."""
    if not REDIS_AVAILABLE:
        return "no-redis"
    token = str(uuid.uuid4())
    key = f"lock:customer:{customer_phone}"
    deadline = _time.monotonic() + timeout_seconds
    while _time.monotonic() < deadline:
        try:
            if redis_client.set(key, token, nx=True, ex=ttl_seconds):
                return token
        except Exception as e:  # noqa: BLE001
            print(f"Redis lock acquire error: {e}")
            return "no-redis"
        _time.sleep(0.2)
    return None


def release_customer_lock(customer_phone: str, token: str) -> None:
    """Releases the lock only if we still hold it. A plain DEL would risk
    deleting a DIFFERENT job's lock in the case where ours already
    expired (TTL hit) and a new job grabbed it in the meantime — the Lua
    script makes the check-and-delete atomic so that race can't happen."""
    if not REDIS_AVAILABLE or token == "no-redis":
        return
    key = f"lock:customer:{customer_phone}"
    lua_release = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    try:
        redis_client.eval(lua_release, 1, key, token)
    except Exception as e:  # noqa: BLE001
        print(f"Redis lock release error: {e}")


def is_duplicate_message(message_sid: str, ttl_seconds: int = 86400) -> bool:
    """True if this Twilio MessageSid has already been claimed once.
    SET NX returns False when the key already existed — meaning we've
    seen this exact delivery before, almost always a Twilio retry.
    Caller should skip enqueueing and just return 200. TTL (24h) only
    needs to outlast Twilio's own retry window, which is much shorter."""
    if not REDIS_AVAILABLE or not message_sid:
        return False
    key = f"processed_msg:{message_sid}"
    try:
        was_new = redis_client.set(key, "1", nx=True, ex=ttl_seconds)
        return not was_new
    except Exception as e:  # noqa: BLE001
        print(f"Redis dedup check error: {e}")
        return False
    
    
# ─── BUSINESS PROMPT CACHE ────────────────────────────────────────────────────
# The business prompt contains the business name, all products,
# and the knowledge base — it almost never changes.
# We cache it for 1 hour so we don't hit PostgreSQL on every message.


def get_cached_business_prompt(business_id: uuid.UUID):
    """
    Returns cached system prompt for a business.
    Returns None if not cached — caller fetches from PostgreSQL.
    """
    if not REDIS_AVAILABLE:
        return None
    try:
        key = f"business_prompt:{business_id}"
        return redis_client.get(key)
    except Exception as e: # noqa: BLE001
        print(f"Redis read error: {e}")
        return None


def cache_business_prompt(business_id: uuid.UUID, prompt: str, ttl_seconds: int = 3600):
    """
    Stores the system prompt in Redis for 1 hour.
    TTL = 3600 seconds — Redis deletes it automatically after 1 hour.
    The next message after expiry fetches fresh data from PostgreSQL.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"business_prompt:{business_id}"
        redis_client.setex(key, ttl_seconds, prompt)
    except Exception as e:  # noqa: BLE001
        print(f"Redis write error: {e}")


def invalidate_business_cache(business_id: uuid.UUID):
    """
    Deletes the cached prompt for a business immediately.
    Call this whenever the business owner updates:
    - their products
    - their knowledge base
    - their business name
    The next customer message will rebuild the prompt from fresh data.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"business_prompt:{business_id}"
        redis_client.delete(key)
        print(f"✓ Cache invalidated for business {business_id}")
    except Exception as e: # noqa: BLE001
        print(f"Redis delete error: {e}")


def invalidate_conversation_cache(
    customer_id: uuid.UUID, business_id: uuid.UUID
) -> None:
    """
    Clears cached conversation for one customer. Used during testing.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"conv:{business_id}:{customer_id}"
        redis_client.delete(key)
        print(
            f"Conversation cache cleared: customer {customer_id} / business {business_id}"
        )
    except Exception as e: # noqa: BLE001
        print(f"Redis delete error: {e}")


# ─── CONVERSATION CACHE ───────────────────────────────────────────────────────
# Active conversations are cached so we don't hit PostgreSQL
# on every message during an ongoing chat.
# Cache expires after 24 hours of inactivity.


def get_cached_conversation(customer_id: uuid.UUID, business_id: uuid.UUID):
    """
    Returns cached conversation history as a list.
    Returns None if not in cache — caller fetches from PostgreSQL.

    Key format: conv:{business_id}:{customer_id}
    The business_id prefix prevents collisions —
    customer 5 at business 1 is different from customer 5 at business 2.
    """
    if not REDIS_AVAILABLE:
        return None
    try:
        key = f"conv:{business_id}:{customer_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"Redis conversation read error: {e}")
        return None


def cache_conversation(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    history: list,
    ttl_seconds: int = 86400,
):
    """
    Stores conversation history in Redis for 24 hours.
    Only keeps the last 10 messages — same limit as our DB fetch.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"conv:{business_id}:{customer_id}"
        recent = history[-10:] if len(history) > 10 else history
        redis_client.setex(key, ttl_seconds, json.dumps(recent))
    except Exception as e:  # noqa: BLE001
        print(f"Redis conversation write error: {e}")


def already_sent_image(
    customer_id: uuid.UUID, business_id: uuid.UUID, product_id: uuid.UUID
) -> bool:
    """
    Checks if a product image has already been sent to this customer.
    Used to prevent duplicate image sends on retried webhook deliveries.
    """
    if not REDIS_AVAILABLE:
        return False
    try:
        key = f"img_sent:{business_id}:{customer_id}:{product_id}"
        exists = redis_client.exists(key)

        print(
            f"[Redis] Checking image key: {key} -> {'already sent' if exists else 'not sent'}"
        )

        return bool(exists)

    except Exception as e: # noqa: BLE001
        print(f"[Redis] Image check error: {e}")
        return False


def mark_image_sent(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    ttl_seconds: int = 86400,
) -> None:
    """
    Records that a product image has already been sent to this customer,
    so `already_sent_image` can prevent duplicate image sends on retried
    webhook deliveries.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"img_sent:{business_id}:{customer_id}:{product_id}"
        redis_client.setex(key, ttl_seconds, "1")
        print(f"[Redis] Image marked as sent: {key}")
    except Exception as e: # noqa: BLE001
        print(f"[Redis] Image mark error: {e}")


def append_to_conversation_cache(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    message: dict,
    ttl_seconds: int = 86400,
):
    """
    Adds one message to the cached conversation.
    Called after every message — both customer and AISHA replies.
    More efficient than rewriting the entire cache each time.
    """
    if not REDIS_AVAILABLE:
        return
    try:
        existing = get_cached_conversation(customer_id, business_id) or []
        existing.append(message)
        cache_conversation(customer_id, business_id, existing, ttl_seconds)
    except Exception as e: # noqa: BLE001
        print(f"Redis append error: {e}")


# ─── ACTIVE BUSINESS SESSION ───────────────────────────────────────────────
# Tracks which business a customer is currently "inside" once they've picked
# one from the list picker, so the open-ended AI branch always answers using
# the store the customer actually selected — not just any active business.
# TTL = 24 hours, same as the conversation cache, so a customer who goes
# quiet reopens the marketplace menu instead of silently staying scoped.


def get_active_business(customer_phone: str):
    """
    Returns the business_id (str) the customer last selected, or None
    if not cached — caller falls back to MarketplaceSession.selected_business_id.
    """
    if not REDIS_AVAILABLE:
        return None
    try:
        key = f"active_biz:{customer_phone}"
        return redis_client.get(key)
    except Exception as e: # noqa: BLE001
        print(f"Redis active business read error: {e}")
        return None


def set_active_business(
    customer_phone: str, business_id: uuid.UUID, ttl_seconds: int = 86400
) -> None:
    """Stores the customer's active business selection in Redis for 24 hours."""
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"active_biz:{customer_phone}"
        redis_client.setex(key, ttl_seconds, str(business_id))
    except Exception as e: # noqa: BLE001
        print(f"Redis active business write error: {e}")


def clear_active_business(customer_phone: str) -> None:
    """Clears the customer's active business selection (e.g. on 'menu'/switch)."""
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"active_biz:{customer_phone}"
        redis_client.delete(key)
    except Exception as e:  # noqa: BLE001
        print(f"Redis active business delete error: {e}")
        
        
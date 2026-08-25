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
        redis_client = redis.from_url(
            redis_url, decode_responses=True, ssl_cert_reqs=None
        )
    else:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    print("Redis Connected successfully")
    REDIS_AVAILABLE = True
except Exception as e:  # noqa: BLE001
    print(f"Redis not available: {e} - running without cache")
    REDIS_AVAILABLE = False
    redis_client = None


LOCK_TTL_SECONDS = 30


# ─── PROMPT VERSIONING ─────────────────────────────────────────────────────
# Fingerprints everything that shapes a business prompt, so any change to the
# persona file or the renderer automatically produces a new cache key. Old
# keys for the previous version are orphaned and never read again — they age
# out on their own TTL, so no manual `DEL business_prompt:*` is needed after a
# prompt edit and there's no risk of serving a stale prompt for up to an hour.
#
# This used to hash `build_system_prompt.__code__.co_code`, which was wrong in
# a way that made the whole mechanism inert: build_system_prompt() is not on
# the runtime prompt path at all (KnowledgeBaseManager.render_and_verify is),
# so editing the real prompt source never moved the version. Worse, the
# version was never actually mixed into the Redis key, so a 0-byte
# aisha_voice.txt stayed cached as a generic fallback prompt for a full hour.
#
# What we hash instead:
#   1. The bytes of the resolved persona file (aisha_voice.txt). This is the
#      big one — it's the file humans actually edit.
#   2. The renderer's bytecode, so changing the prompt layout also busts.
# SYSTEM_PROMPT_SUFFIX is deliberately NOT included: service.py appends it
# *after* the cache lookup, so it can never be stale in a cached value.
def get_prompt_version() -> str:
    """Returns an 8-char fingerprint of the current prompt definition.

    Never raises. A prompt whose version can't be computed still gets a
    stable-per-process key, so a transient read error degrades to "cache is
    a bit stickier than usual" rather than taking the message path down.
    """
    digest = hashlib.md5()

    try:
        from app.knowledge_base.manager import _resolve_system_prompt_path

        path = _resolve_system_prompt_path()
        # Read fresh rather than through manager's lru_cache: the point of
        # this function is to notice content changes, and a memoized read
        # would keep returning the bytes from process start.
        digest.update(path.read_bytes() if path.is_file() else b"<missing-persona>")
    except Exception as e:  # noqa: BLE001 — versioning must never break a message
        print(f"[Prompt version] persona file unreadable: {e}")
        digest.update(b"<unreadable-persona>")

    try:
        from app.knowledge_base.manager import KnowledgeBaseManager

        digest.update(KnowledgeBaseManager.render_and_verify.__code__.co_code)
    except Exception as e:  # noqa: BLE001
        print(f"[Prompt version] renderer bytecode unavailable: {e}")

    return digest.hexdigest()[:8]


def _business_prompt_key(business_id: uuid.UUID) -> str:
    """Single source of truth for the prompt cache key.

    Every reader and writer goes through this, so the version segment can
    never end up on one side of the cache but not the other — which would
    silently turn the cache into a permanent miss (or a permanent stale hit).
    """
    return f"business_prompt:{get_prompt_version()}:{business_id}"


def acquire_customer_lock(
    customer_phone: str,
    timeout_seconds: float = 60,
    ttl_seconds: int = LOCK_TTL_SECONDS,
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
        return redis_client.get(_business_prompt_key(business_id))
    except Exception as e:  # noqa: BLE001
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
        redis_client.setex(_business_prompt_key(business_id), ttl_seconds, prompt)
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
        # Delete every prompt-version variant for this business, not just the
        # one the current code would write. An owner editing their products
        # must not be able to leave an older-version entry behind that a
        # rolled-back deploy would then start reading again. scan_iter is used
        # instead of KEYS because Upstash/Redis KEYS blocks the whole server.
        deleted = 0
        for key in redis_client.scan_iter(
            match=f"business_prompt:*:{business_id}", count=100
        ):
            redis_client.delete(key)
            deleted += 1

        # Pre-versioning keys had no version segment. Kept so an in-place
        # deploy doesn't strand the old-format entry for a full hour.
        redis_client.delete(f"business_prompt:{business_id}")

        print(
            f"✓ Cache invalidated for business {business_id} ({deleted} versioned entries)"
        )
    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
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

    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
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
    except Exception as e:  # noqa: BLE001
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

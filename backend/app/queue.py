import os

from redis import Redis
from rq import Queue

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# ssl_cert_reqs is only a valid/needed argument for TLS connections
# (rediss://, e.g. Upstash in production). Passing it unconditionally
# breaks plain redis:// connections (e.g. local dev) — redis-py's
# connection class rejects it outright when there's no SSL involved.
if _redis_url.startswith("rediss://"):
    _redis_conn = Redis.from_url(_redis_url, ssl_cert_reqs=None)
else:
    _redis_conn = Redis.from_url(_redis_url)

message_queue = Queue("messages", connection=_redis_conn, default_timeout=120)

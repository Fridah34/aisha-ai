import os

import redis
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("REDIS_URL")
print(f"Connecting to: {url[:30]}...")

try:
    redis_client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
        ssl_cert_reqs=None,  # required for Upstash SSL on Windows
    )
    redis_client.ping()
    print("Redis connected successfully")
    REDIS_AVAILABLE = True
except Exception as e:  # noqa: BLE001
    print(f"Redis not available: {e} — running without cache")
    REDIS_AVAILABLE = False
    redis_client = None

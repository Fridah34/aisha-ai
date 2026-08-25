"""RQ worker entrypoint — consumes the `messages` queue.

app/webhook/router.py is a producer only: it parses the Twilio payload and
enqueues app.tasks.message_processor.process_customer_message_job, then acks
200 immediately. This module is the consumer half of that pair. Without it
jobs pile up in Redis as QUEUED forever and AISHA never replies.

The Redis connection is imported from app.queue rather than rebuilt here, so
the worker and the API are guaranteed to be on the same Upstash instance with
the same TLS settings. That's also why we don't use the `rq worker` CLI —
Upstash's rediss:// endpoint needs ssl_cert_reqs=None, which app/queue.py
already handles and the CLI has no way to pass through.

with_scheduler=True is required: the webhook enqueues with
Retry(max=3, interval=[5, 30, 120]), and interval-based retries are handed to
RQ's scheduler. Without it, a retried job would sit in the scheduled registry
and never be requeued.
"""

import logging

from dotenv import find_dotenv, load_dotenv
from rq import Worker

# Must run BEFORE `from app.queue import ...`: app/queue.py resolves REDIS_URL
# at module-import time and silently falls back to redis://localhost:6379 if
# it's unset, which would leave this worker polling an empty local queue while
# the API enqueues to Upstash. app/webhook/router.py loads dotenv before its
# own app.queue import for the same reason.
load_dotenv(find_dotenv())

from app.queue import message_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    worker = Worker([message_queue], connection=message_queue.connection)
    print(
        f"[Worker] Listening on queues: {[q.name for q in worker.queues]}", flush=True
    )
    worker.work(with_scheduler=True)

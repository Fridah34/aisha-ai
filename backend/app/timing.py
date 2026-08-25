"""Millisecond stage timing with a correlation id.

The webhook and the worker are separate processes, so queue wait time is only
visible if both sides stamp the same message. The webhook mints a trace_id and
puts it in the job payload; the worker reads it back and reports
`worker_pickup` as (dequeue time - enqueue time), which is the queue wait —
distinct from processing time.

Emits the format the existing [TIMING] prints already use, so `grep TIMING`
keeps working, but at millisecond resolution instead of `.2f` seconds.
"""

import time
import uuid
from contextlib import contextmanager


def new_trace_id() -> str:
    return uuid.uuid4().hex[:8]


def log_stage(stage: str, ms: float, trace_id: str | None = None) -> None:
    tag = f"[{trace_id}] " if trace_id else ""
    print(f"[TIMING] {tag}{stage}: {ms:.0f} ms", flush=True)


@contextmanager
def stage(name: str, trace_id: str | None = None):
    """Times a block and logs it. Logs even if the block raises, so a failing
    stage still reports how long it burned before failing."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        log_stage(name, (time.perf_counter() - t0) * 1000, trace_id)


class Stopwatch:
    """Cumulative timer for a whole message. `split()` reports one stage and
    resets the interval clock; `total()` reports since construction."""

    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or new_trace_id()
        self._start = time.perf_counter()
        self._last = self._start

    def split(self, stage_name: str) -> float:
        now = time.perf_counter()
        ms = (now - self._last) * 1000
        self._last = now
        log_stage(stage_name, ms, self.trace_id)
        return ms

    def total(self, stage_name: str = "TOTAL") -> float:
        ms = (time.perf_counter() - self._start) * 1000
        log_stage(stage_name, ms, self.trace_id)
        return ms

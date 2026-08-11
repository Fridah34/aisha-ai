"""
Waiting-time helpers. Waiting time is deliberately never stored — it is
always derived from `HandoverEvent.waiting_start_time` at read/notify time.
"""

from __future__ import annotations

from datetime import datetime, timezone


def calculate_waiting_seconds(waiting_start_time: datetime, *, now: datetime | None = None) -> float:
    """Seconds elapsed since `waiting_start_time`."""
    reference = now or datetime.now(timezone.utc)
    if waiting_start_time.tzinfo is None:
        waiting_start_time = waiting_start_time.replace(tzinfo=timezone.utc)
    return max(0.0, (reference - waiting_start_time).total_seconds())


def format_waiting_duration(waiting_start_time: datetime, *, now: datetime | None = None) -> str:
    """Human-readable waiting duration, e.g. "7 minutes", "1 hour 12 minutes".

    Matches the granularity requested for the dashboard/notification copy —
    seconds round down to whole minutes, and hours only appear once waiting
    has crossed 60 minutes.
    """
    total_seconds = int(calculate_waiting_seconds(waiting_start_time, now=now))
    total_minutes = total_seconds // 60

    if total_minutes < 1:
        return "Just now"

    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    parts = [f"{hours} hour{'s' if hours != 1 else ''}"]
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)

"""Choose the Global Ask relative-time instant without collapsing clocks.

`event_occurred_at` is the source-system event instant (Allen, 1983;
Hobbs & Pan, 2017). `created_at` is ``prov:generatedAtTime`` for the
stored record. A bulk import that clusters ingestion time must not hide
yesterday's events. Missing event time falls back to created_at and is
named as that fallback -- never invented.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

__all__ = [
    "TIME_AXIS_CREATED",
    "TIME_AXIS_EVENT",
    "ask_filter_instant",
    "row_matches_time_range",
    "seoul_calendar_date",
    "time_axis_evidence_fact",
]

_SEOUL = ZoneInfo("Asia/Seoul")
TIME_AXIS_EVENT = "time axis: event occurred at"
TIME_AXIS_CREATED = "time axis: record created at"


def _row_get(source_post_row: Any, field_name: str) -> Any:
    if isinstance(source_post_row, Mapping) or hasattr(source_post_row, "get"):
        return source_post_row.get(field_name)
    try:
        return source_post_row[field_name]
    except (KeyError, TypeError):
        return None


def seoul_calendar_date(timestamp_value: object) -> date | None:
    """Return the Asia/Seoul calendar day for a timestamp or date."""
    if timestamp_value is None:
        return None
    if isinstance(timestamp_value, datetime):
        filter_instant = (
            timestamp_value
            if timestamp_value.tzinfo is not None
            else timestamp_value.replace(tzinfo=timezone.utc)
        )
        return filter_instant.astimezone(_SEOUL).date()
    if isinstance(timestamp_value, date):
        return timestamp_value
    return None


def ask_filter_instant(source_post_row: Any) -> object:
    """Prefer event time; fall back to record ingestion time."""
    event_occurred_at = _row_get(source_post_row, "event_occurred_at")
    if event_occurred_at is not None:
        return event_occurred_at
    return _row_get(source_post_row, "created_at")


def time_axis_evidence_fact(
    source_post_row: Any, *, time_filter_active: bool
) -> tuple[str, ...]:
    """Name the clock that the relative-time window used, or nothing."""
    if not time_filter_active:
        return ()
    if _row_get(source_post_row, "event_occurred_at") is not None:
        return (TIME_AXIS_EVENT,)
    if _row_get(source_post_row, "created_at") is not None:
        return (TIME_AXIS_CREATED,)
    return ()


def row_matches_time_range(
    source_post_row: Any,
    time_range: tuple[date, date] | None,
) -> bool:
    """Keep rows inside the Seoul window, or keep them when clocks are absent."""
    if time_range is None:
        return True
    filter_instant = ask_filter_instant(source_post_row)
    calendar_day = seoul_calendar_date(filter_instant)
    if calendar_day is None:
        return True
    range_start, range_end = time_range
    return range_start <= calendar_day <= range_end

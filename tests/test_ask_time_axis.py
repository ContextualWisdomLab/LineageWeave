"""Event time wins over clustered ingestion time for Global Ask filters."""

from __future__ import annotations

from datetime import date, datetime, timezone

from lineageweave.ask_time_axis import (
    TIME_AXIS_CREATED,
    TIME_AXIS_EVENT,
    ask_filter_instant,
    row_matches_time_range,
    seoul_calendar_date,
    time_axis_evidence_fact,
)

_IMPORT_CLUSTER = datetime(2026, 8, 22, 6, 0, tzinfo=timezone.utc)  # 15:00 KST
_YESTERDAY_EVENT = datetime(2026, 8, 21, 3, 0, tzinfo=timezone.utc)
_DAY_BEFORE_EVENT = datetime(2026, 8, 20, 3, 0, tzinfo=timezone.utc)
_LAST_WEEK_EVENT = datetime(2026, 8, 12, 3, 0, tzinfo=timezone.utc)


def test_event_time_wins_over_clustered_created_at() -> None:
    row = {"event_occurred_at": _YESTERDAY_EVENT, "created_at": _IMPORT_CLUSTER}

    assert ask_filter_instant(row) == _YESTERDAY_EVENT
    assert seoul_calendar_date(ask_filter_instant(row)) == date(2026, 8, 21)
    assert time_axis_evidence_fact(row, time_filter_active=True) == (TIME_AXIS_EVENT,)


def test_missing_event_time_falls_back_to_created_at_and_names_that_axis() -> None:
    row = {"event_occurred_at": None, "created_at": _IMPORT_CLUSTER}

    assert ask_filter_instant(row) == _IMPORT_CLUSTER
    assert time_axis_evidence_fact(row, time_filter_active=True) == (TIME_AXIS_CREATED,)
    assert time_axis_evidence_fact(row, time_filter_active=False) == ()


def test_bulk_import_cluster_keeps_spread_event_days() -> None:
    yesterday = {
        "post_id": "yesterday-event",
        "created_at": _IMPORT_CLUSTER,
        "event_occurred_at": _YESTERDAY_EVENT,
    }
    day_before = {
        "post_id": "day-before-event",
        "created_at": _IMPORT_CLUSTER,
        "event_occurred_at": _DAY_BEFORE_EVENT,
    }
    last_week = {
        "post_id": "last-week-event",
        "created_at": _IMPORT_CLUSTER,
        "event_occurred_at": _LAST_WEEK_EVENT,
    }
    ingestion_only = {
        "post_id": "ingestion-only",
        "created_at": _IMPORT_CLUSTER,
        "event_occurred_at": None,
    }

    yesterday_window = (date(2026, 8, 21), date(2026, 8, 21))
    day_before_window = (date(2026, 8, 20), date(2026, 8, 20))
    last_week_window = (date(2026, 8, 10), date(2026, 8, 16))

    assert row_matches_time_range(yesterday, yesterday_window)
    assert not row_matches_time_range(day_before, yesterday_window)
    assert not row_matches_time_range(last_week, yesterday_window)
    assert not row_matches_time_range(ingestion_only, yesterday_window)

    assert row_matches_time_range(day_before, day_before_window)
    assert not row_matches_time_range(yesterday, day_before_window)

    assert row_matches_time_range(last_week, last_week_window)
    assert not row_matches_time_range(yesterday, last_week_window)
    assert row_matches_time_range(ingestion_only, None)

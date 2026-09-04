"""Direct branch tests for the Ask relative-time axis helpers.

The suite exercises Seoul-window filtering and evidence-naming; these
target the remaining guards: non-Mapping rows, None/invalid clocks,
timezone-naive timestamps, and the event/created clock selection.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from lineageweave.ask_time_axis import (
    ask_filter_instant,
    row_matches_time_range,
    seoul_calendar_date,
    time_axis_evidence_fact,
)


def test_row_get_supports_mapping_and_mapping_like_and_sequence_guard() -> None:
    from lineageweave.ask_time_axis import _row_get

    assert _row_get({"a": 1}, "a") == 1
    assert _row_get({"a": 1}, "b") is None
    assert _row_get(["x"], 0) == "x"
    assert _row_get({"a": 1}, 3) is None
    assert _row_get(None, "a") is None


def test_seoul_calendar_date_handles_none_date_and_naive_datetime() -> None:
    assert seoul_calendar_date(None) is None
    assert seoul_calendar_date(date(2026, 1, 5)) == date(2026, 1, 5)
    # A naive UTC-ish timestamp is interpreted as UTC then shifted to Seoul.
    naive = datetime(2026, 1, 5, 15, 0)
    assert seoul_calendar_date(naive) == date(2026, 1, 6)
    aware = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)
    assert seoul_calendar_date(aware) == date(2026, 1, 6)
    assert seoul_calendar_date("not-a-date") is None


def test_ask_filter_instant_falls_back_event_to_created_to_none() -> None:
    assert ask_filter_instant({"event_occurred_at": 1, "created_at": 2}) == 1
    assert ask_filter_instant({"created_at": 2}) == 2
    assert ask_filter_instant({}) is None


@pytest.mark.parametrize(
    ("row", "active", "expected"),
    [
        ({"event_occurred_at": 1, "created_at": 2}, True, ("time axis: event occurred at",)),
        ({"created_at": 2}, True, ("time axis: record created at",)),
        ({"created_at": 2}, False, ()),
        ({}, True, ()),
    ],
)
def test_time_axis_evidence_fact_names_the_active_clock(
    row: dict[str, int], active: bool, expected: tuple[str, ...]
) -> None:
    assert time_axis_evidence_fact(row, time_filter_active=active) == expected


def test_row_matches_time_range_keeps_absent_clocks_when_window_is_active() -> None:
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    window = (start, end)
    assert row_matches_time_range({}, window) is True
    assert row_matches_time_range(
        {"event_occurred_at": datetime(2026, 1, 15, tzinfo=UTC)}, window
    ) is True
    assert row_matches_time_range(
        {"event_occurred_at": datetime(2026, 12, 31, tzinfo=UTC)}, window
    ) is False
    assert row_matches_time_range({}, None) is True

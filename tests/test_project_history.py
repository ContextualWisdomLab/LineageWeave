from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lineageweave.project_history import (
    PROJECT_HISTORY_ONTOLOGY_BASE,
    ProjectHistoryValidationError,
    ResponsibilityInterval,
    event_ontology_iri,
    order_event_rows,
    parse_rfc3339,
    responsibility_handover_gaps,
    serialize_rfc3339,
)


def test_parse_and_serialize_rfc3339_require_an_explicit_offset() -> None:
    value = parse_rfc3339("2026-02-03T09:00:00Z")
    assert value.utcoffset() is not None
    assert serialize_rfc3339(value) == "2026-02-03T09:00:00Z"
    assert parse_rfc3339("2026-02-03T18:00:00+09:00").hour == 18
    assert serialize_rfc3339(None) is None

    with pytest.raises(ProjectHistoryValidationError, match="non-empty"):
        parse_rfc3339("")
    with pytest.raises(ProjectHistoryValidationError, match="RFC 3339"):
        parse_rfc3339("not-a-time")
    with pytest.raises(ProjectHistoryValidationError, match="UTC offset"):
        parse_rfc3339("2026-02-03T09:00:00")
    with pytest.raises(ProjectHistoryValidationError, match="UTC offset"):
        serialize_rfc3339(datetime(2026, 2, 3, 9))


def test_event_ontology_iri_is_typed_and_unknown_codes_fail_to_the_base_class() -> None:
    assert event_ontology_iri("project_event_voc").endswith("VoiceOfCustomerEvent")
    assert event_ontology_iri("future_event") == (
        f"{PROJECT_HISTORY_ONTOLOGY_BASE}ProjectHistoryEvent"
    )


def test_order_event_rows_is_deterministic_for_equal_timestamps() -> None:
    rows = [
        {"project_history_event_id": "b", "occurred_at": "2026-02-03T09:00:00Z"},
        {
            "project_history_event_id": "a",
            "occurred_at": datetime(2026, 2, 3, 9, tzinfo=timezone.utc),
        },
        {
            "project_history_event_id": "earlier",
            "occurred_at": "2022-03-14T09:00:00+00:00",
        },
    ]
    ordered = order_event_rows(rows)
    assert [row["project_history_event_id"] for row in ordered] == [
        "earlier",
        "a",
        "b",
    ]

    with pytest.raises(ProjectHistoryValidationError, match="datetime or RFC 3339"):
        order_event_rows([{"project_history_event_id": "bad", "occurred_at": None}])
    with pytest.raises(ProjectHistoryValidationError, match="UTC offset"):
        order_event_rows(
            [{"project_history_event_id": "bad", "occurred_at": datetime(2026, 1, 1)}]
        )


def test_responsibility_handover_gaps_use_union_coverage() -> None:
    utc = timezone.utc
    assignments = [
        ResponsibilityInterval(
            "long",
            datetime(2022, 3, 1, tzinfo=utc),
            datetime(2023, 5, 20, tzinfo=utc),
        ),
        ResponsibilityInterval(
            "nested",
            datetime(2022, 6, 1, tzinfo=utc),
            datetime(2022, 7, 1, tzinfo=utc),
        ),
        ResponsibilityInterval(
            "pm",
            datetime(2023, 6, 1, tzinfo=utc),
            datetime(2026, 1, 1, tzinfo=utc),
        ),
        ResponsibilityInterval(
            "service",
            datetime(2026, 1, 1, tzinfo=utc),
            None,
        ),
    ]

    gaps = responsibility_handover_gaps(assignments)
    assert len(gaps) == 1
    assert gaps[0].previous_assignment_id == "long"
    assert gaps[0].next_assignment_id == "pm"
    assert gaps[0].gap_seconds == 12 * 86_400


def test_open_assignment_prevents_invented_later_gap() -> None:
    utc = timezone.utc
    assignments = [
        ResponsibilityInterval("current", datetime(2024, 1, 1, tzinfo=utc), None),
        ResponsibilityInterval(
            "later-recorded",
            datetime(2025, 1, 1, tzinfo=utc),
            datetime(2025, 2, 1, tzinfo=utc),
        ),
    ]
    assert responsibility_handover_gaps(assignments) == []


@pytest.mark.parametrize(
    "interval, message",
    [
        (ResponsibilityInterval("naive-start", datetime(2026, 1, 1), None), "valid_from"),
        (
            ResponsibilityInterval(
                "naive-end",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 2),
            ),
            "valid_to",
        ),
        (
            ResponsibilityInterval(
                "negative",
                datetime(2026, 1, 2, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            "precede",
        ),
    ],
)
def test_responsibility_handover_gaps_reject_invalid_intervals(
    interval: ResponsibilityInterval,
    message: str,
) -> None:
    with pytest.raises(ProjectHistoryValidationError, match=message):
        responsibility_handover_gaps([interval])

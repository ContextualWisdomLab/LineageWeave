"""Buyer Calendar consume stays fail-closed and never invents events."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lineageweave.http_client import HttpClientError
from lineageweave.naruon_calendar_projection import NaruonCalendarOccurrence
from lineageweave.naruon_calendar_workspace import (
    NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION,
    NaruonCalendarWorkspaceEvent,
    build_workspace_naruon_client,
    default_calendar_window,
    load_observed_calendar_events,
    occurrence_to_workspace_event,
)


def _occurrence() -> NaruonCalendarOccurrence:
    return NaruonCalendarOccurrence(
        event_reference="evt_001",
        occurrence_reference="occ_001",
        source_reference="src_001",
        provider_revision='W/"revision-7"',
        display_text="Customer review",
        starts_at="2026-08-24T09:00:00+09:00",
        ends_at="2026-08-24T10:00:00+09:00",
        all_day=False,
        time_zone="Asia/Seoul",
        status_code="confirmed",
        disclosure_code="summary_visible",
        truth_status_code="observed",
        observed_at="2026-08-21T00:00:00Z",
    )


def test_default_window_is_thirty_one_utc_days() -> None:
    start, end = default_calendar_window(datetime(2026, 8, 25, 8, 6, tzinfo=timezone.utc))

    assert start == "2026-08-25T08:06:00Z"
    assert end == "2026-09-25T08:06:00Z"


def test_default_window_rejects_a_naive_clock() -> None:
    with pytest.raises(ValueError, match="offset"):
        default_calendar_window(datetime(2026, 8, 25, 8, 6))


def test_missing_audience_does_not_build_a_client() -> None:
    assert build_workspace_naruon_client("", "service-secret") is None
    assert build_workspace_naruon_client("https://naruon.example", "") is None
    assert build_workspace_naruon_client("   ", "   ") is None


def test_malformed_audience_fails_closed_without_a_client() -> None:
    assert build_workspace_naruon_client("file:///tmp/events", "service-secret") is None
    assert (
        build_workspace_naruon_client(
            "https://naruon.example",
            "service secret with space",
        )
        is None
    )


def test_missing_client_keeps_commitments_path_unblocked() -> None:
    result = load_observed_calendar_events(
        None,
        "2026-08-25T00:00:00Z",
        "2026-09-25T00:00:00Z",
    )

    assert result.available is False
    assert result.events == ()
    assert result.next_action == NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION
    assert "token" not in result.next_action.lower()
    assert "secret" not in result.next_action.lower()


def test_transport_failure_does_not_invent_events(monkeypatch) -> None:
    client = build_workspace_naruon_client(
        "https://naruon.example/tenant-projection",
        "service-secret",
    )
    assert client is not None

    def boom(*_args, **_kwargs):
        raise HttpClientError("naruon.example refused the projection")

    monkeypatch.setattr(client, "list_events", boom)
    result = load_observed_calendar_events(
        client,
        "2026-08-25T00:00:00Z",
        "2026-09-25T00:00:00Z",
    )

    assert result.available is False
    assert result.events == ()
    assert result.next_action == NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION


def test_contract_failure_does_not_leak_the_body(monkeypatch) -> None:
    client = build_workspace_naruon_client(
        "https://naruon.example/tenant-projection",
        "service-secret",
    )
    assert client is not None

    def boom(*_args, **_kwargs):
        raise ValueError("calendar_page has unexpected fields: attendees")

    monkeypatch.setattr(client, "list_events", boom)
    result = load_observed_calendar_events(
        client,
        "2026-08-25T00:00:00Z",
        "2026-09-25T00:00:00Z",
    )

    assert result.available is False
    assert result.events == ()
    assert "attendees" not in (result.next_action or "")


def test_accepted_page_keeps_observed_events_out_of_commitments(monkeypatch) -> None:
    client = build_workspace_naruon_client(
        "https://naruon.example/tenant-projection",
        "service-secret",
    )
    assert client is not None
    occurrence = _occurrence()

    class _Page:
        events = (occurrence,)

    monkeypatch.setattr(client, "list_events", lambda *_args, **_kwargs: _Page())
    result = load_observed_calendar_events(
        client,
        "2026-08-25T00:00:00Z",
        "2026-09-25T00:00:00Z",
    )

    assert result.available is True
    assert result.next_action is None
    assert result.events == (occurrence_to_workspace_event(occurrence),)
    assert result.events[0].truth_status_code == "observed"
    assert not hasattr(result.events[0], "issue_ticket_id")
    assert not hasattr(result.events[0], "post_id")


def test_workspace_event_copies_only_admitted_occurrence_fields() -> None:
    event = occurrence_to_workspace_event(_occurrence())

    assert event == NaruonCalendarWorkspaceEvent(
        occurrence_reference="occ_001",
        event_reference="evt_001",
        source_reference="src_001",
        display_text="Customer review",
        starts_at="2026-08-24T09:00:00+09:00",
        ends_at="2026-08-24T10:00:00+09:00",
        all_day=False,
        time_zone="Asia/Seoul",
        status_code="confirmed",
        disclosure_code="summary_visible",
        truth_status_code="observed",
        observed_at="2026-08-21T00:00:00Z",
        provider_revision='W/"revision-7"',
    )

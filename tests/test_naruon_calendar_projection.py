"""Contract tests for the Naruon-owned calendar read projection."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from lineageweave.naruon_calendar_projection import (
    NARUON_CALENDAR_MEDIA_TYPE,
    NaruonCalendarContractError,
    NaruonCalendarOccurrence,
    NaruonCalendarProjectionClient,
    parse_naruon_calendar_page,
)


def _event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "event_reference": "evt_001",
        "occurrence_reference": "occ_001",
        "source_reference": "src_001",
        "provider_revision": 'W/"revision-7"',
        "display_text": "Customer review",
        "starts_at": "2026-08-24T09:00:00+09:00",
        "ends_at": "2026-08-24T10:00:00+09:00",
        "all_day": False,
        "time_zone": "Asia/Seoul",
        "status_code": "confirmed",
        "disclosure_code": "summary_visible",
        "truth_status_code": "observed",
        "observed_at": "2026-08-21T00:00:00Z",
    }
    event.update(overrides)
    return event


def _page(*events: dict[str, object], **overrides: object) -> dict[str, object]:
    page: dict[str, object] = {
        "schema_version": "1.0",
        "projection_revision": "projection_001",
        "events": list(events or (_event(),)),
        "next_cursor": "cursor_002",
    }
    page.update(overrides)
    return page


def test_client_sends_only_service_credential_and_parses_projection(monkeypatch) -> None:
    received: dict[str, object] = {}

    def fake_get_json(
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
        maximum_response_bytes: int | None,
        expected_response_media_type: str | None,
    ) -> dict[str, object]:
        received.update(
            url=url,
            headers=headers,
            timeout=timeout,
            maximum_response_bytes=maximum_response_bytes,
            expected_response_media_type=expected_response_media_type,
        )
        return _page()

    monkeypatch.setattr(
        "lineageweave.naruon_calendar_projection.get_json",
        fake_get_json,
    )
    client = NaruonCalendarProjectionClient(
        "https://naruon.example/tenant-projection/",
        "service-secret",
        maximum_events=25,
        timeout=7,
    )

    page = client.list_events(
        "2026-08-01T00:00:00Z",
        "2026-09-01T00:00:00Z",
        cursor="cursor_001",
    )

    parsed_url = urlparse(str(received["url"]))
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "naruon.example"
    assert parsed_url.path == "/tenant-projection/api/calendar/events"
    assert parse_qs(parsed_url.query) == {
        "window_start": ["2026-08-01T00:00:00Z"],
        "window_end": ["2026-09-01T00:00:00Z"],
        "limit": ["25"],
        "cursor": ["cursor_001"],
    }
    assert received["headers"] == {
        "authorization": "Bearer service-secret",
        "accept": NARUON_CALENDAR_MEDIA_TYPE,
    }
    assert received["timeout"] == 7
    assert received["maximum_response_bytes"] == 1_048_576
    assert received["expected_response_media_type"] == (
        NARUON_CALENDAR_MEDIA_TYPE
    )
    assert page.projection_revision == "projection_001"
    assert page.next_cursor == "cursor_002"
    assert page.events[0].occurrence_reference == "occ_001"
    assert page.events[0].truth_status_code == "observed"


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///tmp/calendar",
        "https://user:secret@naruon.example",
        "https://naruon.example?token=secret",
        "https://naruon.example#events",
        "https://naruon.example/private path",
        "https://naruon.example/private\tpath",
    ],
)
def test_client_rejects_unsafe_base_urls(base_url: str) -> None:
    with pytest.raises((ValueError, NaruonCalendarContractError)):
        NaruonCalendarProjectionClient(base_url, "service-secret")


@pytest.mark.parametrize(
    "token",
    ["", "  ", "secret\nsecond-line", "service secret", "service\tsecret"],
)
def test_client_rejects_missing_control_or_whitespace_tokens(token: str) -> None:
    with pytest.raises(NaruonCalendarContractError):
        NaruonCalendarProjectionClient("https://naruon.example", token)


@pytest.mark.parametrize("maximum_events", [0, 201, True, 1.5])
def test_client_rejects_invalid_page_bounds(maximum_events: object) -> None:
    with pytest.raises(ValueError, match="maximum_events"):
        NaruonCalendarProjectionClient(
            "https://naruon.example",
            "service-secret",
            maximum_events=maximum_events,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "timeout",
    [0, 31, True, float("nan"), float("inf")],
)
def test_client_rejects_invalid_timeouts(timeout: object) -> None:
    with pytest.raises(ValueError, match="timeout"):
        NaruonCalendarProjectionClient(
            "https://naruon.example",
            "service-secret",
            timeout=timeout,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("window_start", "window_end", "message"),
    [
        ("2026-08-01T00:00:00", "2026-08-02T00:00:00Z", "RFC 3339"),
        ("2026-08-02T00:00:00Z", "2026-08-01T00:00:00Z", "after"),
        ("2026-01-01T00:00:00Z", "2027-01-03T00:00:00Z", "366"),
    ],
)
def test_client_rejects_unsafe_windows(
    window_start: str,
    window_end: str,
    message: str,
) -> None:
    client = NaruonCalendarProjectionClient(
        "https://naruon.example",
        "service-secret",
    )
    with pytest.raises((ValueError, NaruonCalendarContractError), match=message):
        client.list_events(window_start, window_end)


def test_client_rejects_url_shaped_cursor_before_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.naruon_calendar_projection.get_json",
        lambda *args, **kwargs: pytest.fail("transport must not run"),
    )
    client = NaruonCalendarProjectionClient(
        "https://naruon.example",
        "service-secret",
    )
    with pytest.raises(NaruonCalendarContractError, match="URL"):
        client.list_events(
            "2026-08-01T00:00:00Z",
            "2026-08-02T00:00:00Z",
            cursor="https://provider.example/private",
        )


def test_parser_preserves_busy_only_policy_filtered_text() -> None:
    page = parse_naruon_calendar_page(
        _page(_event(display_text="Busy", disclosure_code="busy_only"))
    )

    assert page.events[0].display_text == "Busy"
    assert page.events[0].disclosure_code == "busy_only"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("starts_at", "2026-08-24T09:00:00", "RFC 3339"),
        ("starts_at", "2026-08-24 09:00:00+09:00", "RFC 3339"),
        ("starts_at", "2026-08-24T09:00:00+0900", "RFC 3339"),
        ("ends_at", "2026-08-24T08:00:00+09:00", "after starts_at"),
        ("observed_at", "not-a-time", "RFC 3339"),
        ("status_code", "unknown", "unsupported"),
        ("disclosure_code", "full_private_body", "unsupported"),
        ("truth_status_code", "authoritative", "unsupported"),
        ("event_reference", "https://provider.example/event/1", "URL"),
    ],
)
def test_parser_rejects_invalid_occurrence_fields(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(NaruonCalendarContractError, match=message):
        parse_naruon_calendar_page(_page(_event(**{field: value})))


def test_parser_rejects_non_boolean_all_day() -> None:
    with pytest.raises(NaruonCalendarContractError, match="boolean"):
        parse_naruon_calendar_page(_page(_event(all_day="false")))


def test_parser_rejects_duplicate_occurrences() -> None:
    with pytest.raises(NaruonCalendarContractError, match="duplicate"):
        parse_naruon_calendar_page(_page(_event(), deepcopy(_event())))


def test_parser_rejects_unknown_fields() -> None:
    with pytest.raises(NaruonCalendarContractError, match="unexpected"):
        parse_naruon_calendar_page(
            _page(_event(provider_url="https://provider.example"))
        )


def test_parser_rejects_unsupported_schema_and_invalid_roots() -> None:
    with pytest.raises(NaruonCalendarContractError, match="unsupported"):
        parse_naruon_calendar_page(_page(schema_version="2.0"))
    with pytest.raises(NaruonCalendarContractError, match="object"):
        parse_naruon_calendar_page([])
    with pytest.raises(NaruonCalendarContractError, match="array"):
        parse_naruon_calendar_page(_page(events={}))


def test_parser_rejects_over_limit_pages_and_invalid_parser_bounds() -> None:
    events = [_event(occurrence_reference=f"occ_{index}") for index in range(3)]
    with pytest.raises(NaruonCalendarContractError, match="page size"):
        parse_naruon_calendar_page(_page(*events), maximum_events=2)
    for invalid in (0, True, 1.5):
        with pytest.raises(ValueError, match="maximum_events"):
            parse_naruon_calendar_page(
                _page(),
                maximum_events=invalid,  # type: ignore[arg-type]
            )


def test_parser_allows_terminal_page_without_cursor() -> None:
    page = _page()
    page.pop("next_cursor")

    parsed = parse_naruon_calendar_page(page)

    assert parsed.next_cursor is None


def test_parser_rejects_missing_required_fields_and_non_string_text() -> None:
    missing = _event()
    missing.pop("source_reference")
    with pytest.raises(NaruonCalendarContractError, match="missing required"):
        parse_naruon_calendar_page(_page(missing))
    with pytest.raises(NaruonCalendarContractError, match="must be a string"):
        parse_naruon_calendar_page(_page(_event(display_text=123)))


def test_parser_rejects_whitespace_in_opaque_references() -> None:
    with pytest.raises(NaruonCalendarContractError, match="opaque token"):
        parse_naruon_calendar_page(_page(_event(source_reference="source private")))


def test_client_omits_cursor_when_not_requested(monkeypatch) -> None:
    received: dict[str, object] = {}

    def fake_get_json(
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
        maximum_response_bytes: int | None,
        expected_response_media_type: str | None,
    ) -> dict[str, object]:
        del headers, timeout
        received["url"] = url
        received["maximum_response_bytes"] = maximum_response_bytes
        received["expected_response_media_type"] = expected_response_media_type
        return _page()

    monkeypatch.setattr(
        "lineageweave.naruon_calendar_projection.get_json",
        fake_get_json,
    )
    client = NaruonCalendarProjectionClient(
        "https://naruon.example",
        "service-secret",
    )

    client.list_events("2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z")

    assert "cursor" not in parse_qs(urlparse(str(received["url"])).query)
    assert received["maximum_response_bytes"] == 1_048_576
    assert received["expected_response_media_type"] == (
        NARUON_CALENDAR_MEDIA_TYPE
    )


def test_json_schema_matches_parser_contract() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "contracts"
        / "naruon-calendar-projection-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    occurrence_schema = schema["$defs"]["calendar_occurrence"]

    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["events"]["maxItems"] == 200
    assert set(occurrence_schema["required"]) == {
        field.name for field in fields(NaruonCalendarOccurrence)
    }
    assert occurrence_schema["properties"]["truth_status_code"]["const"] == (
        "observed"
    )
    assert schema["$defs"]["opaque_reference"]["pattern"] == (
        r"^(?!.*://)[^\s\u0000-\u001F\u007F]+$"
    )


def test_public_package_exports_calendar_projection_contract() -> None:
    import lineageweave

    assert lineageweave.NARUON_CALENDAR_SCHEMA_VERSION == "1.0"
    assert lineageweave.NaruonCalendarProjectionClient is (
        NaruonCalendarProjectionClient
    )
    assert lineageweave.parse_naruon_calendar_page is parse_naruon_calendar_page

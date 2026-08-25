"""Regression tests for exact calendar contract string boundaries."""

from __future__ import annotations

import pytest

from lineageweave.naruon_calendar_projection import (
    NaruonCalendarContractError,
    NaruonCalendarProjectionClient,
    parse_naruon_calendar_page,
)


def _page(**event_overrides: object) -> dict[str, object]:
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
    event.update(event_overrides)
    return {
        "schema_version": "1.0",
        "projection_revision": "projection_001",
        "events": [event],
        "next_cursor": None,
    }


@pytest.mark.parametrize(
    "token",
    [" service-secret", "service-secret ", "\nservice-secret", "service-secret\n"],
)
def test_service_token_rejects_surrounding_whitespace(token: str) -> None:
    with pytest.raises(NaruonCalendarContractError, match="whitespace"):
        NaruonCalendarProjectionClient("https://naruon.example", token)


@pytest.mark.parametrize(
    "base_url",
    [" https://naruon.example", "https://naruon.example "],
)
def test_base_url_rejects_surrounding_whitespace(base_url: str) -> None:
    with pytest.raises(NaruonCalendarContractError, match="whitespace"):
        NaruonCalendarProjectionClient(base_url, "service-secret")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_reference", " src_001"),
        ("source_reference", "src_001 "),
        ("display_text", " Customer review"),
        ("display_text", "Customer review "),
        ("starts_at", " 2026-08-24T09:00:00+09:00"),
        ("observed_at", "2026-08-21T00:00:00Z "),
    ],
)
def test_projection_rejects_silently_normalized_text(
    field: str,
    value: str,
) -> None:
    with pytest.raises(NaruonCalendarContractError, match="whitespace"):
        parse_naruon_calendar_page(_page(**{field: value}))

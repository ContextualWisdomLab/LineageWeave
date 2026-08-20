from __future__ import annotations

import pytest

from lineageweave.caldav_client import (
    CalDavEvent,
    HttpCalDavClient,
    NullCalDavClient,
    build_caldav_client,
)


def test_missing_base_url_drops_only_the_optional_caldav_channel() -> None:
    client = build_caldav_client("")

    assert isinstance(client, NullCalDavClient)
    assert not client.available
    assert client.list_events() == []


def test_http_client_reads_valid_events_and_ignores_malformed_rows(monkeypatch) -> None:
    received = {}

    def fake_get_json(url: str, *, timeout: float) -> dict:
        received.update(url=url, timeout=timeout)
        return {
            "events": [
                {
                    "event_id": "event-1",
                    "summary": "Review",
                    "starts_at": "2026-08-19T09:00:00Z",
                },
                {
                    "event_id": "event-2",
                    "summary": "",
                    "starts_at": "2026-08-19T10:00:00Z",
                },
                "not-an-event",
            ]
        }

    monkeypatch.setattr("lineageweave.caldav_client.get_json", fake_get_json)
    client = build_caldav_client("https://calendar.example/caldav/")

    assert isinstance(client, HttpCalDavClient)
    assert client.list_events() == [
        CalDavEvent("event-1", "Review", "2026-08-19T09:00:00Z")
    ]
    assert received == {"url": "https://calendar.example/caldav/events", "timeout": 10}


def test_invalid_caldav_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="CALDAV_BASE_URL"):
        build_caldav_client("file:///tmp/events")

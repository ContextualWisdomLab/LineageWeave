"""Small independent CalDAV event-consumption port for the organization calendar."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from lineageweave.http_client import get_json

CALDAV_UNAVAILABLE_NEXT_ACTION = (
    "Configure CALDAV_BASE_URL to connect the independent CalDAV event source."
)


@dataclass(frozen=True)
class CalDavEvent:
    """One calendar event read from the configured CalDAV source."""

    event_id: str
    summary: str
    starts_at: str


class NullCalDavClient:
    """Fail-closed CalDAV client used when CALDAV_BASE_URL is unset; never fabricates events."""

    available = False

    def list_events(self) -> list[CalDavEvent]:
        """Always return no events; there is no CalDAV source to query."""
        return []


class HttpCalDavClient:
    """CalDAV client backed by a real HTTP events endpoint."""

    available = True

    def __init__(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("CALDAV_BASE_URL must be an http(s) URL with a hostname")
        self._events_url = f"{base_url.rstrip('/')}/events"

    def list_events(self) -> list[CalDavEvent]:
        """Fetch and parse events from the configured CalDAV endpoint."""
        payload = get_json(self._events_url, timeout=10)
        rows = payload.get("events")
        if not isinstance(rows, list):
            return []
        events: list[CalDavEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            values = (row.get("event_id"), row.get("summary"), row.get("starts_at"))
            if not all(isinstance(value, str) and value.strip() for value in values):
                continue
            events.append(CalDavEvent(*(value.strip() for value in values)))
        return events


def build_caldav_client(base_url: str) -> NullCalDavClient | HttpCalDavClient:
    """Return the real source only when explicitly configured."""
    normalized = base_url.strip()
    return HttpCalDavClient(normalized) if normalized else NullCalDavClient()

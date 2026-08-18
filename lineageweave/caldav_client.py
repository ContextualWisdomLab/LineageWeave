"""Consume an independent CalDAV module. Do not plant a calendar kernel.

The Officeware CalDAV repo owns storage and the CalDAV server. This
port only reads already-published events when a base URL is configured.
Unset ``CALDAV_BASE_URL`` keeps the channel unavailable. Never invent
an event and never copy post 할 일 rows into this view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from .http_client import HttpClientError, get_json

CALDAV_UNAVAILABLE_NEXT_ACTION = "이 범위의 일정을 아직 받을 수 없습니다"


@dataclass(frozen=True)
class CalDavEvent:
    """One event the CalDAV module already published. No invented title."""

    event_id: str
    summary: str
    starts_at: str


class CalDavClient(Protocol):
    """Calendar consume port. Implementations must not invent events."""

    available: bool

    def list_events(self) -> tuple[CalDavEvent, ...]:
        """Authorized events, or empty when the module is not wired."""


class NullCalDavClient:
    """Default: CalDAV module is not on this machine."""

    available = False

    def list_events(self) -> tuple[CalDavEvent, ...]:
        return ()


class HttpCalDavClient:
    """GET ``{base}/events`` on an operator-configured CalDAV consume port."""

    available = True

    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"unsupported CalDAV base URL scheme: {parsed.scheme or 'missing'}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_events(self) -> tuple[CalDavEvent, ...]:
        try:
            body = get_json(f"{self._base_url}/events", timeout=self._timeout)
        except (OSError, ValueError, HttpClientError):
            return ()
        rows = body.get("events") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            return ()
        events: list[CalDavEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            event_id = str(row.get("event_id") or "").strip()
            summary = str(row.get("summary") or "").strip()
            starts_at = str(row.get("starts_at") or "").strip()
            if not event_id or not summary or not starts_at:
                continue
            events.append(CalDavEvent(event_id=event_id, summary=summary, starts_at=starts_at))
        return tuple(events)


def build_caldav_client(base_url: str) -> CalDavClient:
    """Null when unset. Never plants a CalDAV process or event store."""
    cleaned = base_url.strip()
    if not cleaned:
        return NullCalDavClient()
    return HttpCalDavClient(cleaned)


__all__ = [
    "CALDAV_UNAVAILABLE_NEXT_ACTION",
    "CalDavClient",
    "CalDavEvent",
    "HttpCalDavClient",
    "NullCalDavClient",
    "build_caldav_client",
]

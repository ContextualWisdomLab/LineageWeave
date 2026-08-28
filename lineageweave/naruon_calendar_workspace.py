"""Fail-closed Buyer Calendar consume of Naruon observed occurrences.

LineageWeave commitments stay available when this channel is missing or
malformed. Observed events are never promoted into issue tickets and the
end-user bearer token is never forwarded to Naruon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .http_client import HttpClientError
from .naruon_calendar_projection import (
    NaruonCalendarContractError,
    NaruonCalendarOccurrence,
    NaruonCalendarProjectionClient,
)

NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION = (
    "Ask your workspace administrator to enable calendar access. "
    "Open a commitment below to read its source post."
)
_DEFAULT_WINDOW = timedelta(days=31)


@dataclass(frozen=True)
class NaruonCalendarWorkspaceEvent:
    """Buyer-visible observed occurrence; not a LineageWeave commitment."""

    occurrence_reference: str
    event_reference: str
    source_reference: str
    display_text: str
    starts_at: str
    ends_at: str
    all_day: bool
    time_zone: str
    status_code: str
    disclosure_code: str
    truth_status_code: str
    observed_at: str
    provider_revision: str


@dataclass(frozen=True)
class NaruonCalendarWorkspaceResult:
    """Fail-closed observation page for the Buyer Calendar."""

    available: bool
    next_action: str | None
    events: tuple[NaruonCalendarWorkspaceEvent, ...]


def default_calendar_window(now: datetime) -> tuple[str, str]:
    """Return a 31-day UTC RFC 3339 window starting at ``now``.

    Naive timestamps are rejected so a local clock cannot leak into the
    Naruon consume contract.
    """

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include an offset")
    start = now.astimezone(timezone.utc).replace(microsecond=0)
    end = start + _DEFAULT_WINDOW
    return (
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def occurrence_to_workspace_event(
    occurrence: NaruonCalendarOccurrence,
) -> NaruonCalendarWorkspaceEvent:
    """Copy one validated occurrence into the Buyer Calendar payload."""

    return NaruonCalendarWorkspaceEvent(
        occurrence_reference=occurrence.occurrence_reference,
        event_reference=occurrence.event_reference,
        source_reference=occurrence.source_reference,
        display_text=occurrence.display_text,
        starts_at=occurrence.starts_at,
        ends_at=occurrence.ends_at,
        all_day=occurrence.all_day,
        time_zone=occurrence.time_zone,
        status_code=occurrence.status_code,
        disclosure_code=occurrence.disclosure_code,
        truth_status_code=occurrence.truth_status_code,
        observed_at=occurrence.observed_at,
        provider_revision=occurrence.provider_revision,
    )


def build_workspace_naruon_client(
    base_url: str,
    service_access_token: str,
) -> NaruonCalendarProjectionClient | None:
    """Return a Naruon client only when both transport settings are usable.

    A missing or malformed audience is unavailable, never a fabricated
    event source. The caller must pass the service credential, not an
    end-user bearer token.
    """

    if not base_url.strip() or not service_access_token.strip():
        return None
    try:
        return NaruonCalendarProjectionClient(base_url, service_access_token)
    except ValueError:
        return None


def load_observed_calendar_events(
    client: NaruonCalendarProjectionClient | None,
    window_start: str,
    window_end: str,
) -> NaruonCalendarWorkspaceResult:
    """Read one observed page, or fail closed without inventing events."""

    if client is None:
        return NaruonCalendarWorkspaceResult(
            available=False,
            next_action=NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION,
            events=(),
        )
    try:
        page = client.list_events(window_start, window_end)
    except (HttpClientError, OSError, ValueError, NaruonCalendarContractError):
        return NaruonCalendarWorkspaceResult(
            available=False,
            next_action=NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION,
            events=(),
        )
    return NaruonCalendarWorkspaceResult(
        available=True,
        next_action=None,
        events=tuple(occurrence_to_workspace_event(row) for row in page.events),
    )

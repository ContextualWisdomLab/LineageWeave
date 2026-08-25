"""Strict consumer contract for Naruon-owned calendar event projections.

LineageWeave owns post-grounded commitments and issue tickets. Naruon owns
customer calendar provider access, CalDAV synchronization, provider revisions,
writeback, retry, and reconciliation. This module consumes only a bounded,
already-authorized Naruon read projection; it is deliberately not a CalDAV
client and never receives provider credentials or an end-user bearer token.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

from .http_client import get_json

NARUON_CALENDAR_SCHEMA_VERSION = "1.0"
NARUON_CALENDAR_MEDIA_TYPE = (
    "application/vnd.contextualwisdomlab.naruon-calendar.v1+json"
)
NARUON_CALENDAR_EVENTS_PATH = "/api/calendar/events"
_MAX_WINDOW = timedelta(days=366)
_MAX_RESPONSE_BYTES = 1_048_576
_ALLOWED_STATUS_CODES = frozenset(
    {"confirmed", "tentative", "desired", "cancelled"}
)
_ALLOWED_DISCLOSURE_CODES = frozenset({"busy_only", "summary_visible"})
_ALLOWED_TRUTH_STATUS_CODES = frozenset({"observed"})
_RFC3339_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:"
    r"[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)
_OCCURRENCE_FIELDS = frozenset(
    {
        "event_reference",
        "occurrence_reference",
        "source_reference",
        "provider_revision",
        "display_text",
        "starts_at",
        "ends_at",
        "all_day",
        "time_zone",
        "status_code",
        "disclosure_code",
        "truth_status_code",
        "observed_at",
    }
)


class NaruonCalendarContractError(ValueError):
    """The Naruon calendar projection violated the versioned read contract."""


@dataclass(frozen=True)
class NaruonCalendarOccurrence:
    """One policy-filtered external calendar occurrence observed by Naruon."""

    event_reference: str
    occurrence_reference: str
    source_reference: str
    provider_revision: str
    display_text: str
    starts_at: str
    ends_at: str
    all_day: bool
    time_zone: str
    status_code: str
    disclosure_code: str
    truth_status_code: str
    observed_at: str


@dataclass(frozen=True)
class NaruonCalendarPage:
    """One bounded page of Naruon calendar occurrences and its cursor."""

    schema_version: str
    projection_revision: str
    events: tuple[NaruonCalendarOccurrence, ...]
    next_cursor: str | None


def _strict_object(
    value: Any,
    *,
    field_name: str,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Return a mapping containing exactly the admitted fields."""

    if not isinstance(value, dict):
        raise NaruonCalendarContractError(f"{field_name} must be an object")
    keys = frozenset(value)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise NaruonCalendarContractError(
            f"{field_name} is missing required fields: "
            f"{', '.join(sorted(missing))}"
        )
    if extra:
        raise NaruonCalendarContractError(
            f"{field_name} has unexpected fields: "
            f"{', '.join(sorted(extra))}"
        )
    return value


def _bounded_text(
    value: Any,
    *,
    field_name: str,
    maximum_length: int,
    allow_internal_whitespace: bool = True,
    allow_url_shape: bool = True,
) -> str:
    """Validate exact bounded text without silently normalizing identity."""

    if not isinstance(value, str):
        raise NaruonCalendarContractError(f"{field_name} must be a string")
    if value != value.strip():
        raise NaruonCalendarContractError(
            f"{field_name} must not contain surrounding whitespace"
        )
    if not value or len(value) > maximum_length:
        raise NaruonCalendarContractError(
            f"{field_name} must contain 1..{maximum_length} characters"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise NaruonCalendarContractError(
            f"{field_name} contains control characters"
        )
    if not allow_internal_whitespace and any(
        character.isspace() for character in value
    ):
        raise NaruonCalendarContractError(
            f"{field_name} must be an opaque token without whitespace"
        )
    if not allow_url_shape and "://" in value:
        raise NaruonCalendarContractError(
            f"{field_name} must not contain a URL"
        )
    return value


def _bounded_integer(
    value: Any,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Return one true integer inside an inclusive range."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(  # noqa: TRY004 - public constructor keeps ValueError compatibility.
            f"{field_name} must be an integer"
        )
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{field_name} must be between {minimum} and {maximum}"
        )
    return value


def _bounded_timeout(value: Any) -> float:
    """Return a finite timeout in the supported transport range."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(  # noqa: TRY004 - public constructor keeps ValueError compatibility.
            "timeout must be a finite number"
        )
    timeout = float(value)
    if not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError(
            "timeout must be greater than 0 and at most 30 seconds"
        )
    return timeout


def _opaque_reference(value: Any, *, field_name: str) -> str:
    """Validate a bounded opaque non-URL token."""

    return _bounded_text(
        value,
        field_name=field_name,
        maximum_length=256,
        allow_internal_whitespace=False,
        allow_url_shape=False,
    )


def _parse_rfc3339(value: Any, *, field_name: str) -> datetime:
    """Parse one exact offset-aware RFC 3339 instant."""

    text = _bounded_text(
        value,
        field_name=field_name,
        maximum_length=64,
        allow_internal_whitespace=True,
    )
    if _RFC3339_PATTERN.fullmatch(text) is None:
        raise NaruonCalendarContractError(
            f"{field_name} must be RFC 3339"
        )
    normalized = text[:10] + "T" + text[11:]
    if normalized.endswith(("Z", "z")):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise NaruonCalendarContractError(
            f"{field_name} must be RFC 3339"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NaruonCalendarContractError(
            f"{field_name} must include an offset"
        )
    return parsed


def _controlled_code(
    value: Any,
    *,
    field_name: str,
    allowed: frozenset[str],
) -> str:
    """Validate one closed-vocabulary code."""

    code = _bounded_text(
        value,
        field_name=field_name,
        maximum_length=64,
        allow_internal_whitespace=False,
    )
    if code not in allowed:
        raise NaruonCalendarContractError(
            f"{field_name} has an unsupported value"
        )
    return code


def _parse_occurrence(value: Any, *, index: int) -> NaruonCalendarOccurrence:
    """Parse one strict occurrence from a projection page."""

    field_name = f"events[{index}]"
    row = _strict_object(
        value,
        field_name=field_name,
        required=_OCCURRENCE_FIELDS,
    )
    if not isinstance(row["all_day"], bool):
        raise NaruonCalendarContractError(
            f"{field_name}.all_day must be a boolean"
        )
    starts_text = _bounded_text(
        row["starts_at"],
        field_name=f"{field_name}.starts_at",
        maximum_length=64,
        allow_internal_whitespace=True,
    )
    ends_text = _bounded_text(
        row["ends_at"],
        field_name=f"{field_name}.ends_at",
        maximum_length=64,
        allow_internal_whitespace=True,
    )
    observed_text = _bounded_text(
        row["observed_at"],
        field_name=f"{field_name}.observed_at",
        maximum_length=64,
        allow_internal_whitespace=True,
    )
    starts_at = _parse_rfc3339(starts_text, field_name=f"{field_name}.starts_at")
    ends_at = _parse_rfc3339(ends_text, field_name=f"{field_name}.ends_at")
    _parse_rfc3339(observed_text, field_name=f"{field_name}.observed_at")
    if ends_at <= starts_at:
        raise NaruonCalendarContractError(
            f"{field_name}.ends_at must be after starts_at"
        )
    return NaruonCalendarOccurrence(
        event_reference=_opaque_reference(
            row["event_reference"], field_name=f"{field_name}.event_reference"
        ),
        occurrence_reference=_opaque_reference(
            row["occurrence_reference"],
            field_name=f"{field_name}.occurrence_reference",
        ),
        source_reference=_opaque_reference(
            row["source_reference"], field_name=f"{field_name}.source_reference"
        ),
        provider_revision=_bounded_text(
            row["provider_revision"],
            field_name=f"{field_name}.provider_revision",
            maximum_length=256,
            allow_url_shape=False,
        ),
        display_text=_bounded_text(
            row["display_text"],
            field_name=f"{field_name}.display_text",
            maximum_length=512,
        ),
        starts_at=starts_text,
        ends_at=ends_text,
        all_day=row["all_day"],
        time_zone=_bounded_text(
            row["time_zone"],
            field_name=f"{field_name}.time_zone",
            maximum_length=128,
            allow_internal_whitespace=False,
        ),
        status_code=_controlled_code(
            row["status_code"],
            field_name=f"{field_name}.status_code",
            allowed=_ALLOWED_STATUS_CODES,
        ),
        disclosure_code=_controlled_code(
            row["disclosure_code"],
            field_name=f"{field_name}.disclosure_code",
            allowed=_ALLOWED_DISCLOSURE_CODES,
        ),
        truth_status_code=_controlled_code(
            row["truth_status_code"],
            field_name=f"{field_name}.truth_status_code",
            allowed=_ALLOWED_TRUTH_STATUS_CODES,
        ),
        observed_at=observed_text,
    )


def parse_naruon_calendar_page(
    payload: Any,
    *,
    maximum_events: int = 200,
) -> NaruonCalendarPage:
    """Validate and convert one Naruon calendar projection page."""

    admitted_maximum = _bounded_integer(
        maximum_events,
        field_name="maximum_events",
        minimum=1,
        maximum=200,
    )
    root = _strict_object(
        payload,
        field_name="calendar_page",
        required=frozenset(
            {"schema_version", "projection_revision", "events"}
        ),
        optional=frozenset({"next_cursor"}),
    )
    if root["schema_version"] != NARUON_CALENDAR_SCHEMA_VERSION:
        raise NaruonCalendarContractError(
            "calendar_page.schema_version is unsupported"
        )
    projection_revision = _opaque_reference(
        root["projection_revision"],
        field_name="calendar_page.projection_revision",
    )
    rows = root["events"]
    if not isinstance(rows, list):
        raise NaruonCalendarContractError(
            "calendar_page.events must be an array"
        )
    if len(rows) > admitted_maximum:
        raise NaruonCalendarContractError(
            "calendar_page.events exceeds the admitted page size"
        )
    events = tuple(
        _parse_occurrence(row, index=index) for index, row in enumerate(rows)
    )
    occurrence_references = [event.occurrence_reference for event in events]
    if len(occurrence_references) != len(set(occurrence_references)):
        raise NaruonCalendarContractError(
            "calendar_page contains duplicate occurrence references"
        )
    next_cursor_value = root.get("next_cursor")
    next_cursor = (
        None
        if next_cursor_value is None
        else _bounded_text(
            next_cursor_value,
            field_name="calendar_page.next_cursor",
            maximum_length=1024,
            allow_internal_whitespace=False,
            allow_url_shape=False,
        )
    )
    return NaruonCalendarPage(
        schema_version=NARUON_CALENDAR_SCHEMA_VERSION,
        projection_revision=projection_revision,
        events=events,
        next_cursor=next_cursor,
    )


class NaruonCalendarProjectionClient:
    """Read a bounded Naruon calendar projection with a service credential."""

    def __init__(
        self,
        base_url: str,
        service_access_token: str,
        *,
        maximum_events: int = 200,
        timeout: float = 10.0,
    ) -> None:
        """Validate immutable transport settings for one Naruon audience."""

        normalized_base = _bounded_text(
            base_url,
            field_name="base_url",
            maximum_length=2048,
            allow_internal_whitespace=False,
        )
        parsed = urlparse(normalized_base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(
                "base_url must be an http(s) URL with a hostname"
            )
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url must not contain userinfo")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        token = _bounded_text(
            service_access_token,
            field_name="service_access_token",
            maximum_length=4096,
            allow_internal_whitespace=False,
        )
        self._events_url = (
            f"{normalized_base.rstrip('/')}{NARUON_CALENDAR_EVENTS_PATH}"
        )
        self._service_access_token = token
        self._maximum_events = _bounded_integer(
            maximum_events,
            field_name="maximum_events",
            minimum=1,
            maximum=200,
        )
        self._timeout = _bounded_timeout(timeout)

    def list_events(
        self,
        window_start: str,
        window_end: str,
        *,
        cursor: str | None = None,
    ) -> NaruonCalendarPage:
        """Return one authorized event page within an offset-aware window."""

        start_text = _bounded_text(
            window_start,
            field_name="window_start",
            maximum_length=64,
            allow_internal_whitespace=False,
        )
        end_text = _bounded_text(
            window_end,
            field_name="window_end",
            maximum_length=64,
            allow_internal_whitespace=False,
        )
        starts_at = _parse_rfc3339(start_text, field_name="window_start")
        ends_at = _parse_rfc3339(end_text, field_name="window_end")
        if ends_at <= starts_at:
            raise ValueError("window_end must be after window_start")
        if ends_at - starts_at > _MAX_WINDOW:
            raise ValueError("calendar window must not exceed 366 days")
        fields = {
            "window_start": start_text,
            "window_end": end_text,
            "limit": str(self._maximum_events),
        }
        if cursor is not None:
            fields["cursor"] = _bounded_text(
                cursor,
                field_name="cursor",
                maximum_length=1024,
                allow_internal_whitespace=False,
                allow_url_shape=False,
            )
        payload = get_json(
            f"{self._events_url}?{urlencode(fields)}",
            headers={
                "authorization": f"Bearer {self._service_access_token}",
                "accept": NARUON_CALENDAR_MEDIA_TYPE,
            },
            timeout=self._timeout,
            maximum_response_bytes=_MAX_RESPONSE_BYTES,
            expected_response_media_type=NARUON_CALENDAR_MEDIA_TYPE,
        )
        return parse_naruon_calendar_page(
            payload,
            maximum_events=self._maximum_events,
        )

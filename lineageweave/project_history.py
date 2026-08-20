"""Pure project-lifecycle ordering and handover-gap contracts.

The database stores evidence-backed project events and responsibility
assignments. This module contains deterministic, side-effect-free logic used
by the API projection and tests: RFC 3339 parsing/serialization, event
ordering, ontology identifiers, and positive handover-gap detection.

A gap describes uncovered time between visible assignments. It is not proof
that no work occurred, and it is never manufactured for overlapping,
open-ended, naive, or invalid intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

PROJECT_HISTORY_ONTOLOGY_BASE = (
    "https://contextualwisdomlab.github.io/lineageweave/project-history#"
)

_EVENT_ONTOLOGY_TERMS = {
    "project_event_order": "OrderAwardEvent",
    "project_event_spec_change": "SpecificationChangeEvent",
    "project_event_delivery": "DeliveryEvent",
    "project_event_voc": "VoiceOfCustomerEvent",
    "project_event_rebid": "RebidEvent",
}


class ProjectHistoryValidationError(ValueError):
    """Raised when a project-history timestamp or interval is invalid."""


@dataclass(frozen=True)
class ResponsibilityInterval:
    """One evidence-visible responsibility assignment interval."""

    assignment_id: str
    valid_from: datetime
    valid_to: datetime | None


@dataclass(frozen=True)
class HandoverGap:
    """A positive uncovered interval between visible responsibility spans."""

    previous_assignment_id: str
    next_assignment_id: str
    gap_start: datetime
    gap_end: datetime
    gap_seconds: float


def parse_rfc3339(value: str, *, field: str = "timestamp") -> datetime:
    """Parse an offset-aware RFC 3339 timestamp."""

    if not isinstance(value, str) or not value.strip():
        raise ProjectHistoryValidationError(
            f"{field} must be a non-empty RFC 3339 timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectHistoryValidationError(
            f"{field} must be an RFC 3339 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProjectHistoryValidationError(f"{field} must include a UTC offset")
    return parsed


def serialize_rfc3339(value: datetime | None, *, field: str = "timestamp") -> str | None:
    """Serialize an aware timestamp with ``Z`` for UTC and fail closed on naive input."""

    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProjectHistoryValidationError(f"{field} must include a UTC offset")
    return value.isoformat().replace("+00:00", "Z")


def event_ontology_iri(event_type_code: str) -> str:
    """Return the versioned project-history ontology IRI for a registered event type."""

    term = _EVENT_ONTOLOGY_TERMS.get(event_type_code)
    if term is None:
        return f"{PROJECT_HISTORY_ONTOLOGY_BASE}ProjectHistoryEvent"
    return f"{PROJECT_HISTORY_ONTOLOGY_BASE}{term}"


def order_event_rows(rows: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Return event mappings ordered by occurrence time and stable event id."""

    def key(row: Mapping[str, object]) -> tuple[datetime, str]:
        occurred_at = row.get("occurred_at")
        if isinstance(occurred_at, datetime):
            parsed = occurred_at
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ProjectHistoryValidationError(
                    "occurred_at must include a UTC offset"
                )
        elif isinstance(occurred_at, str):
            parsed = parse_rfc3339(occurred_at, field="occurred_at")
        else:
            raise ProjectHistoryValidationError(
                "occurred_at must be a datetime or RFC 3339 string"
            )
        return parsed, str(row.get("project_history_event_id") or "")

    return sorted(rows, key=key)


def responsibility_handover_gaps(
    assignments: Sequence[ResponsibilityInterval],
) -> list[HandoverGap]:
    """Return positive gaps in the union of visible assignment intervals.

    Nested or overlapping assignments extend coverage and cannot create a false
    gap. An open-ended assignment covers all subsequent time, so no later gap
    can be proven from the visible evidence.
    """

    ordered = sorted(assignments, key=lambda item: (item.valid_from, item.assignment_id))
    for assignment in ordered:
        if assignment.valid_from.tzinfo is None or assignment.valid_from.utcoffset() is None:
            raise ProjectHistoryValidationError("valid_from must include a UTC offset")
        if assignment.valid_to is not None:
            if assignment.valid_to.tzinfo is None or assignment.valid_to.utcoffset() is None:
                raise ProjectHistoryValidationError("valid_to must include a UTC offset")
            if assignment.valid_to < assignment.valid_from:
                raise ProjectHistoryValidationError(
                    "valid_to must not precede valid_from"
                )

    if not ordered:
        return []

    gaps: list[HandoverGap] = []
    coverage_owner = ordered[0]
    coverage_end = ordered[0].valid_to

    for following in ordered[1:]:
        if coverage_end is None:
            break
        if following.valid_from > coverage_end:
            gaps.append(
                HandoverGap(
                    previous_assignment_id=coverage_owner.assignment_id,
                    next_assignment_id=following.assignment_id,
                    gap_start=coverage_end,
                    gap_end=following.valid_from,
                    gap_seconds=(following.valid_from - coverage_end).total_seconds(),
                )
            )
        if following.valid_to is None or following.valid_to > coverage_end:
            coverage_owner = following
            coverage_end = following.valid_to

    return gaps

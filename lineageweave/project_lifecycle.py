"""Validated input contracts for authoritative project-lifecycle imports.

This module deliberately contains no title/body classifier.  A source adapter
must provide an explicit external event code; PostgreSQL resolves that code
through the versioned mapping registry before an authoritative row is written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from typing import Any
from unicodedata import normalize
from uuid import UUID

from .project_history import normalize_project_key

PROJECT_EVENT_TYPE_CODES = frozenset(
    {
        "project_event_order",
        "project_event_spec_change",
        "project_event_delivery",
        "project_event_voc",
        "project_event_rebid",
    }
)
PROJECT_ACTOR_TYPE_CODES = frozenset({"prov_person", "prov_organization", "prov_team"})
PROJECT_RELATION_TYPE_CODES = frozenset({"project_relation_precedes", "project_relation_related"})


class ProjectLifecycleValidationError(ValueError):
    """Raised when an import would create unsupported lifecycle evidence."""


@dataclass(frozen=True)
class ProjectLifecycleRelationInput:
    """One explicit relation to an already imported event in the same project."""

    target_source_system_code: str
    target_source_record_key: str
    relation_type_code: str
    evidence_post_id: str


@dataclass(frozen=True)
class ProjectLifecycleResponsibilityInput:
    """One explicit responsibility assignment with its own evidence post."""

    actor_type_code: str
    actor_key: str
    actor_name: str
    responsibility_text: str
    evidence_post_id: str


@dataclass(frozen=True)
class ProjectLifecycleEventInput:
    """One source-owned lifecycle record accepted by the writer boundary."""

    project_key: str
    project_name: str
    source_system_code: str
    source_record_key: str
    source_event_code: str
    mapping_version: str
    event_started_at: datetime
    event_ended_at: datetime | None
    evidence_post_id: str
    relations: tuple[ProjectLifecycleRelationInput, ...] = field(default_factory=tuple)
    responsibilities: tuple[ProjectLifecycleResponsibilityInput, ...] = field(
        default_factory=tuple
    )


def _required_text(value: object, field_name: str) -> str:
    """Return normalized non-empty text for a trusted application boundary."""

    if not isinstance(value, str) or not value.strip():
        raise ProjectLifecycleValidationError(f"{field_name} must be non-empty text")
    return normalize("NFKC", value).strip()


def _offset_aware(value: datetime, field_name: str) -> None:
    """Require an offset-aware timestamp so event order is deterministic."""

    if not isinstance(value, datetime):
        raise ProjectLifecycleValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProjectLifecycleValidationError(f"{field_name} must include a timezone offset")


def _uuid_text(value: object, field_name: str) -> str:
    """Validate an evidence identifier before the database UUID cast."""

    text = _required_text(value, field_name)
    try:
        return str(UUID(text))
    except ValueError as exc:
        raise ProjectLifecycleValidationError(f"{field_name} must be a UUID") from exc


def validate_project_lifecycle_event(event: ProjectLifecycleEventInput) -> str:
    """Validate one event and return its canonical project identity key.

    The external source code is intentionally not classified here.  The
    mapping registry is the only authority for translating it to a registered
    event type.  This keeps an LLM or a title/body heuristic outside the write
    path.
    """

    try:
        project_key = normalize_project_key(_required_text(event.project_key, "project_key"))
    except ValueError as exc:
        raise ProjectLifecycleValidationError(str(exc)) from exc
    _required_text(event.project_name, "project_name")
    source_system_code = _required_text(event.source_system_code, "source_system_code")
    source_record_key = _required_text(event.source_record_key, "source_record_key")
    _required_text(event.source_event_code, "source_event_code")
    _required_text(event.mapping_version, "mapping_version")
    _uuid_text(event.evidence_post_id, "evidence_post_id")
    _offset_aware(event.event_started_at, "event_started_at")
    if event.event_ended_at is not None:
        _offset_aware(event.event_ended_at, "event_ended_at")
        if event.event_ended_at < event.event_started_at:
            raise ProjectLifecycleValidationError("event_ended_at cannot precede event_started_at")

    for relation in event.relations:
        target_source_system_code = _required_text(
            relation.target_source_system_code, "relation.target_source_system_code"
        )
        target_source_record_key = _required_text(
            relation.target_source_record_key, "relation.target_source_record_key"
        )
        if relation.relation_type_code not in PROJECT_RELATION_TYPE_CODES:
            raise ProjectLifecycleValidationError(
                f"unsupported relation_type_code: {relation.relation_type_code!r}"
            )
        _uuid_text(relation.evidence_post_id, "relation.evidence_post_id")
        if (
            target_source_system_code == source_system_code
            and target_source_record_key == source_record_key
        ):
            raise ProjectLifecycleValidationError("an event cannot relate to itself")

    for responsibility in event.responsibilities:
        if responsibility.actor_type_code not in PROJECT_ACTOR_TYPE_CODES:
            raise ProjectLifecycleValidationError(
                f"unsupported actor_type_code: {responsibility.actor_type_code!r}"
            )
        _required_text(responsibility.actor_key, "responsibility.actor_key")
        _required_text(responsibility.actor_name, "responsibility.actor_name")
        _required_text(responsibility.responsibility_text, "responsibility.responsibility_text")
        _uuid_text(responsibility.evidence_post_id, "responsibility.evidence_post_id")
    return project_key


def project_lifecycle_digest(event: ProjectLifecycleEventInput) -> str:
    """Return a stable, non-PII digest for audit and idempotent replacement."""

    validate_project_lifecycle_event(event)

    def serializable(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "__dataclass_fields__"):
            return {name: serializable(getattr(value, name)) for name in value.__dataclass_fields__}
        if isinstance(value, tuple):
            return [serializable(item) for item in value]
        return value

    encoded = json.dumps(serializable(event), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_project_lifecycle_write_permission(permission_codes: set[str]) -> None:
    """Require the dedicated writer permission, separate from ``post_read``."""

    if "project_lifecycle_write" not in permission_codes:
        raise PermissionError("project_lifecycle_write permission is required")


__all__ = [
    "PROJECT_ACTOR_TYPE_CODES",
    "PROJECT_EVENT_TYPE_CODES",
    "PROJECT_RELATION_TYPE_CODES",
    "ProjectLifecycleEventInput",
    "ProjectLifecycleRelationInput",
    "ProjectLifecycleResponsibilityInput",
    "ProjectLifecycleValidationError",
    "project_lifecycle_digest",
    "require_project_lifecycle_write_permission",
    "validate_project_lifecycle_event",
]

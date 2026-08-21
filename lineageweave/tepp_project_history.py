"""Strict LineageWeave client for TEPP project-history projections.

LineageWeave selects authorized source evidence. TEPP validates the knowledge
cutoff, orders explicit events, and returns coded temporal associations. This
module never supplies provider credentials, never treats event order as
causality, and never accepts a theta or an unpublished score field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from lineageweave.http_client import HttpClientError, post_json

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_PATH = "/v1/project-histories"
PROJECT_HISTORY_INFERENCE_STATUS = "temporal_association_only"
PROJECT_HISTORY_CONSUMER_CODE = "lineageweave"

Transport = Callable[[dict[str, Any], dict[str, str]], dict[str, Any]]


class TeppProjectHistoryNotAvailable(RuntimeError):
    """TEPP project-history transport is absent or returned an unusable result."""


def _parse_timestamp(value: object, field_name: str) -> datetime:
    """Parse one timezone-aware RFC 3339-like timestamp or fail closed."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include an offset")
    return parsed


def _require_exact_keys(payload: dict[str, Any], expected: frozenset[str], name: str) -> None:
    """Reject missing or unpublished fields in a versioned TEPP envelope."""
    actual = frozenset(payload)
    if actual != expected:
        raise ValueError(f"invalid {name} fields")


def _require_text(value: object, field_name: str, maximum: int = 4096) -> str:
    """Return bounded non-empty text from an untrusted wire value."""
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{field_name} must be bounded non-empty text")
    return value


@dataclass(frozen=True)
class ProjectHistoryEvent:
    """One explicit, source-grounded event sent to or returned by TEPP."""

    event_id: str
    event_type_code: str
    event_title: str
    occurred_at: str
    available_at: str
    availability_basis_code: str
    source_post_id: str
    evidence_text: str
    actor_ids: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        """Serialize this event without post bodies or identity labels."""
        return {
            "event_id": self.event_id,
            "event_type_code": self.event_type_code,
            "event_title": self.event_title,
            "occurred_at": self.occurred_at,
            "available_at": self.available_at,
            "availability_basis_code": self.availability_basis_code,
            "source_post_id": self.source_post_id,
            "evidence_text": self.evidence_text,
            "actor_ids": list(self.actor_ids),
        }

    @classmethod
    def from_json(cls, payload: object) -> ProjectHistoryEvent:
        """Parse one strict TEPP event from an untrusted JSON object."""
        if not isinstance(payload, dict):
            raise ValueError("project-history event must be an object")
        expected = frozenset(
            {
                "event_id",
                "event_type_code",
                "event_title",
                "occurred_at",
                "available_at",
                "availability_basis_code",
                "source_post_id",
                "evidence_text",
                "actor_ids",
            }
        )
        _require_exact_keys(payload, expected, "project-history event")
        actor_ids = payload["actor_ids"]
        if not isinstance(actor_ids, list) or len(actor_ids) > 64:
            raise ValueError("actor_ids must be a bounded list")
        parsed_actor_ids = tuple(_require_text(value, "actor_id", 256) for value in actor_ids)
        occurred_at = _require_text(payload["occurred_at"], "occurred_at", 64)
        available_at = _require_text(payload["available_at"], "available_at", 64)
        _parse_timestamp(occurred_at, "occurred_at")
        _parse_timestamp(available_at, "available_at")
        return cls(
            event_id=_require_text(payload["event_id"], "event_id", 256),
            event_type_code=_require_text(payload["event_type_code"], "event_type_code", 64),
            event_title=_require_text(payload["event_title"], "event_title", 512),
            occurred_at=occurred_at,
            available_at=available_at,
            availability_basis_code=_require_text(
                payload["availability_basis_code"], "availability_basis_code", 64
            ),
            source_post_id=_require_text(payload["source_post_id"], "source_post_id", 256),
            evidence_text=_require_text(payload["evidence_text"], "evidence_text"),
            actor_ids=parsed_actor_ids,
        )


@dataclass(frozen=True)
class ProjectHistoryRequest:
    """Versioned TEPP request built only from authorized project evidence."""

    contract_version: int
    idempotency_key: str
    tenant_workspace_id: str
    project_key: str
    project_name: str
    knowledge_cutoff: str
    focus_event_id: str
    events: tuple[ProjectHistoryEvent, ...]

    def to_json(self) -> dict[str, Any]:
        """Serialize the exact public TEPP request contract."""
        return {
            "contract_version": self.contract_version,
            "idempotency_key": self.idempotency_key,
            "tenant_workspace_id": self.tenant_workspace_id,
            "project_key": self.project_key,
            "project_name": self.project_name,
            "knowledge_cutoff": self.knowledge_cutoff,
            "focus_event_id": self.focus_event_id,
            "events": [event.to_json() for event in self.events],
        }


@dataclass(frozen=True)
class ProjectHistoryFinding:
    """One TEPP-coded temporal association and its source evidence."""

    finding_code: str
    summary: str
    related_event_ids: tuple[str, ...]
    evidence_post_ids: tuple[str, ...]

    @classmethod
    def from_json(cls, payload: object) -> ProjectHistoryFinding:
        """Parse one strict temporal finding."""
        if not isinstance(payload, dict):
            raise ValueError("project-history finding must be an object")
        expected = frozenset(
            {"finding_code", "summary", "related_event_ids", "evidence_post_ids"}
        )
        _require_exact_keys(payload, expected, "project-history finding")
        related = payload["related_event_ids"]
        evidence = payload["evidence_post_ids"]
        if not isinstance(related, list) or not isinstance(evidence, list) or not evidence:
            raise ValueError("project-history finding must name its evidence")
        return cls(
            finding_code=_require_text(payload["finding_code"], "finding_code", 128),
            summary=_require_text(payload["summary"], "summary"),
            related_event_ids=tuple(_require_text(value, "related_event_id", 256) for value in related),
            evidence_post_ids=tuple(_require_text(value, "evidence_post_id", 256) for value in evidence),
        )


@dataclass(frozen=True)
class ProjectHistoryProjection:
    """Validated TEPP response rendered by LineageWeave buyer surfaces."""

    contract_version: int
    project_key: str
    project_name: str
    focus_event_id: str
    history_span_start: str
    history_span_end: str
    participant_count: int
    inference_status: str
    events: tuple[ProjectHistoryEvent, ...]
    findings: tuple[ProjectHistoryFinding, ...]

    @classmethod
    def from_json(cls, payload: object) -> ProjectHistoryProjection:
        """Parse and validate the complete public TEPP projection."""
        if not isinstance(payload, dict):
            raise ValueError("project-history projection must be an object")
        expected = frozenset(
            {
                "contract_version",
                "project_key",
                "project_name",
                "focus_event_id",
                "history_span_start",
                "history_span_end",
                "participant_count",
                "inference_status",
                "events",
                "findings",
            }
        )
        _require_exact_keys(payload, expected, "project-history projection")
        if payload["contract_version"] != PROJECT_HISTORY_CONTRACT_VERSION:
            raise ValueError("unsupported project-history contract version")
        if payload["inference_status"] != PROJECT_HISTORY_INFERENCE_STATUS:
            raise ValueError("project-history projection must remain non-causal")
        participant_count = payload["participant_count"]
        if isinstance(participant_count, bool) or not isinstance(participant_count, int) or participant_count < 0:
            raise ValueError("participant_count must be a non-negative integer")
        raw_events = payload["events"]
        raw_findings = payload["findings"]
        if not isinstance(raw_events, list) or not raw_events or not isinstance(raw_findings, list):
            raise ValueError("project-history projection requires event and finding lists")
        events = tuple(ProjectHistoryEvent.from_json(event) for event in raw_events)
        findings = tuple(ProjectHistoryFinding.from_json(finding) for finding in raw_findings)
        event_ids = [event.event_id for event in events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("project-history projection contains duplicate events")
        focus_event_id = _require_text(payload["focus_event_id"], "focus_event_id", 256)
        if focus_event_id not in set(event_ids):
            raise ValueError("project-history focus event is absent")
        occurred = [_parse_timestamp(event.occurred_at, "occurred_at") for event in events]
        if occurred != sorted(occurred):
            raise ValueError("project-history events are not ordered")
        history_span_start = _require_text(payload["history_span_start"], "history_span_start", 64)
        history_span_end = _require_text(payload["history_span_end"], "history_span_end", 64)
        if _parse_timestamp(history_span_start, "history_span_start") > _parse_timestamp(
            history_span_end, "history_span_end"
        ):
            raise ValueError("project-history span is inverted")
        return cls(
            contract_version=PROJECT_HISTORY_CONTRACT_VERSION,
            project_key=_require_text(payload["project_key"], "project_key", 256),
            project_name=_require_text(payload["project_name"], "project_name", 512),
            focus_event_id=focus_event_id,
            history_span_start=history_span_start,
            history_span_end=history_span_end,
            participant_count=participant_count,
            inference_status=PROJECT_HISTORY_INFERENCE_STATUS,
            events=events,
            findings=findings,
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize the validated projection for the API and frontend."""
        return {
            "contract_version": self.contract_version,
            "project_key": self.project_key,
            "project_name": self.project_name,
            "focus_event_id": self.focus_event_id,
            "history_span_start": self.history_span_start,
            "history_span_end": self.history_span_end,
            "participant_count": self.participant_count,
            "inference_status": self.inference_status,
            "events": [event.to_json() for event in self.events],
            "findings": [
                {
                    "finding_code": finding.finding_code,
                    "summary": finding.summary,
                    "related_event_ids": list(finding.related_event_ids),
                    "evidence_post_ids": list(finding.evidence_post_ids),
                }
                for finding in self.findings
            ],
        }


def _no_transport(_payload: dict[str, Any], _headers: dict[str, str]) -> dict[str, Any]:
    """Fail closed when no TEPP project-history endpoint is configured."""
    raise TeppProjectHistoryNotAvailable("TEPP project-history transport is not configured")


class TeppProjectHistoryClient:
    """Submit strict project-history requests through a replaceable transport."""

    def __init__(self, transport: Transport = _no_transport) -> None:
        self._transport = transport

    @property
    def available(self) -> bool:
        """Return whether this client has a configured transport."""
        return self._transport is not _no_transport

    def project(self, request: ProjectHistoryRequest) -> ProjectHistoryProjection:
        """Submit a request and validate TEPP's exact non-causal response."""
        headers = {
            "tepp-consumer": PROJECT_HISTORY_CONSUMER_CODE,
            "tepp-contract-version": str(PROJECT_HISTORY_CONTRACT_VERSION),
            "idempotency-key": request.idempotency_key,
        }
        try:
            payload = self._transport(request.to_json(), headers)
        except TeppProjectHistoryNotAvailable:
            raise
        except (HttpClientError, OSError, TypeError, ValueError) as exc:
            raise TeppProjectHistoryNotAvailable(str(exc)) from exc
        return ProjectHistoryProjection.from_json(payload)


def configured_tepp_project_history_client(url: str) -> TeppProjectHistoryClient:
    """Build an HTTP TEPP client from an exact project-history endpoint URL."""
    target = url.strip()
    if not target:
        return TeppProjectHistoryClient()

    def transport(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        try:
            return post_json(target, payload, headers=headers, timeout=30.0)
        except (HttpClientError, OSError, TypeError, ValueError) as exc:
            raise TeppProjectHistoryNotAvailable(str(exc)) from exc

    return TeppProjectHistoryClient(transport=transport)

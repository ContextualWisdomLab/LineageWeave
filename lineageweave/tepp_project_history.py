"""Strict LineageWeave client for TEPP project-history projections.

LineageWeave owns authorization and selects an exact project evidence bundle.
TEPP owns the versioned temporal projection.  The boundary is intentionally
credential-free: browser bearer tokens, review credentials, provider keys, and
LineageWeave database access never cross into TEPP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from lineageweave.http_client import HttpClientError, post_json

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_PATH = "/v1/project-histories"
TEMPORAL_ASSOCIATION_ONLY = "temporal_association_only"
_MAX_EVENTS = 128
_MAX_ACTORS_PER_EVENT = 64
_MAX_EVIDENCE_TEXT = 2_000
_MAX_IDENTITY_TEXT = 256


class TeppProjectHistoryUnavailable(RuntimeError):
    """Raised when TEPP cannot return a trustworthy project-history projection."""


def _require_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TeppProjectHistoryUnavailable(f"{name} must be an object")
    return value


def _require_closed_fields(
    payload: Mapping[str, Any],
    allowed: set[str],
    *,
    name: str,
) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise TeppProjectHistoryUnavailable(
            f"{name} contains unsupported fields: {', '.join(sorted(unknown))}"
        )


def _require_text(value: Any, *, name: str, maximum: int = _MAX_IDENTITY_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > maximum:
        raise TeppProjectHistoryUnavailable(f"{name} is missing or exceeds its byte limit")
    if any(ord(character) < 0x20 for character in value):
        raise TeppProjectHistoryUnavailable(f"{name} contains a control character")
    return value.strip()


def _parse_utc_timestamp(value: Any, *, name: str) -> datetime:
    raw = _require_text(value, name=name, maximum=64)
    if not raw.endswith("Z"):
        raise TeppProjectHistoryUnavailable(f"{name} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable(f"{name} is not RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise TeppProjectHistoryUnavailable(f"{name} must be UTC")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ProjectHistoryEvent:
    """One explicitly observed project event sent to or returned by TEPP."""

    event_id: str
    event_type_code: str
    event_title: str
    event_time: str
    available_at: str
    availability_basis: str
    source_post_id: str
    evidence_text: str
    actor_ids: tuple[str, ...] = ()

    _FIELDS = {
        "event_id",
        "event_type_code",
        "event_title",
        "event_time",
        "available_at",
        "availability_basis",
        "source_post_id",
        "evidence_text",
        "actor_ids",
    }

    def to_wire(self, *, cutoff: datetime | None = None) -> dict[str, Any]:
        """Validate and serialize this event without inferring missing evidence."""
        event_time = _parse_utc_timestamp(self.event_time, name="event_time")
        available_at = _parse_utc_timestamp(self.available_at, name="available_at")
        if cutoff is not None and available_at > cutoff:
            raise TeppProjectHistoryUnavailable("event was unavailable at the knowledge cutoff")
        actor_ids = tuple(dict.fromkeys(self.actor_ids))
        if len(actor_ids) > _MAX_ACTORS_PER_EVENT:
            raise TeppProjectHistoryUnavailable("event actor count exceeds the contract limit")
        return {
            "event_id": _require_text(self.event_id, name="event_id"),
            "event_type_code": _require_text(
                self.event_type_code, name="event_type_code", maximum=96
            ),
            "event_title": _require_text(self.event_title, name="event_title", maximum=512),
            "event_time": _utc_text(event_time),
            "available_at": _utc_text(available_at),
            "availability_basis": _require_text(
                self.availability_basis, name="availability_basis", maximum=128
            ),
            "source_post_id": _require_text(self.source_post_id, name="source_post_id"),
            "evidence_text": _require_text(
                self.evidence_text, name="evidence_text", maximum=_MAX_EVIDENCE_TEXT
            ),
            "actor_ids": [
                _require_text(actor_id, name="actor_id") for actor_id in actor_ids
            ],
        }

    @classmethod
    def from_wire(cls, value: Any) -> "ProjectHistoryEvent":
        """Parse one strict event object from a TEPP response."""
        payload = _require_mapping(value, name="event")
        _require_closed_fields(payload, cls._FIELDS, name="event")
        actor_ids_value = payload.get("actor_ids")
        if not isinstance(actor_ids_value, list):
            raise TeppProjectHistoryUnavailable("event.actor_ids must be a list")
        event = cls(
            event_id=_require_text(payload.get("event_id"), name="event_id"),
            event_type_code=_require_text(
                payload.get("event_type_code"), name="event_type_code", maximum=96
            ),
            event_title=_require_text(
                payload.get("event_title"), name="event_title", maximum=512
            ),
            event_time=_require_text(payload.get("event_time"), name="event_time", maximum=64),
            available_at=_require_text(
                payload.get("available_at"), name="available_at", maximum=64
            ),
            availability_basis=_require_text(
                payload.get("availability_basis"), name="availability_basis", maximum=128
            ),
            source_post_id=_require_text(
                payload.get("source_post_id"), name="source_post_id"
            ),
            evidence_text=_require_text(
                payload.get("evidence_text"),
                name="evidence_text",
                maximum=_MAX_EVIDENCE_TEXT,
            ),
            actor_ids=tuple(
                _require_text(actor_id, name="actor_id") for actor_id in actor_ids_value
            ),
        )
        event.to_wire()
        return event


@dataclass(frozen=True)
class ProjectHistoryRequest:
    """Versioned exact-project evidence request sent from LineageWeave to TEPP."""

    contract_version: int
    idempotency_key: str
    tenant_workspace_id: str
    project_key: str
    project_name: str
    knowledge_cutoff: str
    focus_event_id: str
    events: tuple[ProjectHistoryEvent, ...]

    def to_wire(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Validate and serialize the request at a fixed receipt clock."""
        if self.contract_version != PROJECT_HISTORY_CONTRACT_VERSION:
            raise TeppProjectHistoryUnavailable("unsupported project-history contract version")
        receipt = now or datetime.now(timezone.utc)
        if receipt.tzinfo is None:
            receipt = receipt.replace(tzinfo=timezone.utc)
        cutoff = _parse_utc_timestamp(self.knowledge_cutoff, name="knowledge_cutoff")
        if cutoff > receipt.astimezone(timezone.utc):
            raise TeppProjectHistoryUnavailable("knowledge cutoff is after request receipt")
        if not self.events or len(self.events) > _MAX_EVENTS:
            raise TeppProjectHistoryUnavailable("event count is outside the contract bounds")
        wire_events = [event.to_wire(cutoff=cutoff) for event in self.events]
        event_ids = [str(event["event_id"]) for event in wire_events]
        if len(set(event_ids)) != len(event_ids):
            raise TeppProjectHistoryUnavailable("event identities must be unique")
        focus_event_id = _require_text(self.focus_event_id, name="focus_event_id")
        if focus_event_id not in event_ids:
            raise TeppProjectHistoryUnavailable("focus event is outside the supplied evidence bundle")
        return {
            "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
            "idempotency_key": _require_text(
                self.idempotency_key, name="idempotency_key"
            ),
            "tenant_workspace_id": _require_text(
                self.tenant_workspace_id, name="tenant_workspace_id"
            ),
            "project_key": _require_text(self.project_key, name="project_key"),
            "project_name": _require_text(
                self.project_name, name="project_name", maximum=512
            ),
            "knowledge_cutoff": _utc_text(cutoff),
            "focus_event_id": focus_event_id,
            "events": wire_events,
        }


@dataclass(frozen=True)
class ProjectHistoryFinding:
    """One TEPP temporal-association finding over explicit supplied events."""

    finding_code: str
    summary: str
    related_event_ids: tuple[str, ...]
    evidence_post_ids: tuple[str, ...]

    _FIELDS = {
        "finding_code",
        "summary",
        "related_event_ids",
        "evidence_post_ids",
    }

    @classmethod
    def from_wire(
        cls,
        value: Any,
        *,
        event_ids: set[str],
        source_post_ids: set[str],
    ) -> "ProjectHistoryFinding":
        """Parse a finding and keep every reference inside the authorized bundle."""
        payload = _require_mapping(value, name="finding")
        _require_closed_fields(payload, cls._FIELDS, name="finding")
        related = payload.get("related_event_ids")
        evidence = payload.get("evidence_post_ids")
        if not isinstance(related, list) or not isinstance(evidence, list):
            raise TeppProjectHistoryUnavailable("finding references must be lists")
        related_ids = tuple(
            _require_text(item, name="related_event_id") for item in related
        )
        evidence_ids = tuple(
            _require_text(item, name="evidence_post_id") for item in evidence
        )
        if not related_ids or not evidence_ids:
            raise TeppProjectHistoryUnavailable("finding must cite events and source posts")
        if not set(related_ids).issubset(event_ids) or not set(evidence_ids).issubset(
            source_post_ids
        ):
            raise TeppProjectHistoryUnavailable(
                "TEPP finding references evidence outside the authorized bundle"
            )
        summary = _require_text(payload.get("summary"), name="finding.summary", maximum=2_000)
        lowered_summary = summary.casefold()
        non_causal_boundary = any(
            marker in lowered_summary
            for marker in ("not causal", "not a causal", "non-causal", "non causal")
        )
        if "temporal association" not in lowered_summary or not non_causal_boundary:
            raise TeppProjectHistoryUnavailable("finding summary omitted temporal/non-causal boundary")
        return cls(
            finding_code=_require_text(
                payload.get("finding_code"), name="finding_code", maximum=96
            ),
            summary=summary,
            related_event_ids=related_ids,
            evidence_post_ids=evidence_ids,
        )

    def to_wire(self) -> dict[str, Any]:
        """Serialize this validated finding for the LineageWeave API."""
        return {
            "finding_code": self.finding_code,
            "summary": self.summary,
            "related_event_ids": list(self.related_event_ids),
            "evidence_post_ids": list(self.evidence_post_ids),
        }


@dataclass(frozen=True)
class ProjectHistoryProjection:
    """Strict TEPP project-history projection accepted by LineageWeave."""

    contract_version: int
    project_key: str
    project_name: str
    focus_event_id: str
    inference_status: str
    participant_count: int
    history_span_start: str
    history_span_end: str
    events: tuple[ProjectHistoryEvent, ...]
    findings: tuple[ProjectHistoryFinding, ...]

    _FIELDS = {
        "contract_version",
        "project_key",
        "project_name",
        "focus_event_id",
        "inference_status",
        "participant_count",
        "history_span_start",
        "history_span_end",
        "events",
        "findings",
    }

    @classmethod
    def from_wire(
        cls,
        value: Any,
        *,
        request: ProjectHistoryRequest,
    ) -> "ProjectHistoryProjection":
        """Validate a TEPP response against the exact submitted evidence bundle."""
        payload = _require_mapping(value, name="project_history")
        _require_closed_fields(payload, cls._FIELDS, name="project_history")
        if payload.get("contract_version") != PROJECT_HISTORY_CONTRACT_VERSION:
            raise TeppProjectHistoryUnavailable("unsupported response contract version")
        if payload.get("inference_status") != TEMPORAL_ASSOCIATION_ONLY:
            raise TeppProjectHistoryUnavailable("TEPP response attempted unsupported authority")
        raw_events = payload.get("events")
        raw_findings = payload.get("findings")
        if not isinstance(raw_events, list) or not isinstance(raw_findings, list):
            raise TeppProjectHistoryUnavailable("project history events/findings must be lists")
        events = tuple(ProjectHistoryEvent.from_wire(event) for event in raw_events)
        if len(events) != len(request.events):
            raise TeppProjectHistoryUnavailable("TEPP response changed the evidence cardinality")
        request_by_id = {event.event_id: event.to_wire() for event in request.events}
        event_by_id = {event.event_id: event.to_wire() for event in events}
        if request_by_id != event_by_id:
            raise TeppProjectHistoryUnavailable("TEPP response changed supplied event evidence")
        chronological = sorted(
            events,
            key=lambda event: (
                _parse_utc_timestamp(event.event_time, name="event_time"),
                event.event_id,
            ),
        )
        if list(events) != chronological:
            raise TeppProjectHistoryUnavailable("TEPP events are not in deterministic time order")
        focus_event_id = _require_text(
            payload.get("focus_event_id"), name="focus_event_id"
        )
        if focus_event_id != request.focus_event_id:
            raise TeppProjectHistoryUnavailable("TEPP response changed the focus event")
        project_key = _require_text(payload.get("project_key"), name="project_key")
        project_name = _require_text(
            payload.get("project_name"), name="project_name", maximum=512
        )
        if project_key != request.project_key or project_name != request.project_name:
            raise TeppProjectHistoryUnavailable("TEPP response changed project identity")
        participant_count = payload.get("participant_count")
        actor_count = len({actor for event in events for actor in event.actor_ids})
        if not isinstance(participant_count, int) or participant_count != actor_count:
            raise TeppProjectHistoryUnavailable("participant count is not evidence-derived")
        span_start = _parse_utc_timestamp(
            payload.get("history_span_start"), name="history_span_start"
        )
        span_end = _parse_utc_timestamp(
            payload.get("history_span_end"), name="history_span_end"
        )
        if not events or span_start != _parse_utc_timestamp(
            events[0].event_time, name="event_time"
        ) or span_end != _parse_utc_timestamp(events[-1].event_time, name="event_time"):
            raise TeppProjectHistoryUnavailable("history span does not match ordered events")
        event_ids = set(event_by_id)
        source_post_ids = {event.source_post_id for event in events}
        findings = tuple(
            ProjectHistoryFinding.from_wire(
                finding,
                event_ids=event_ids,
                source_post_ids=source_post_ids,
            )
            for finding in raw_findings
        )
        return cls(
            contract_version=PROJECT_HISTORY_CONTRACT_VERSION,
            project_key=project_key,
            project_name=project_name,
            focus_event_id=focus_event_id,
            inference_status=TEMPORAL_ASSOCIATION_ONLY,
            participant_count=participant_count,
            history_span_start=_utc_text(span_start),
            history_span_end=_utc_text(span_end),
            events=events,
            findings=findings,
        )

    def to_wire(self) -> dict[str, Any]:
        """Serialize the trusted projection for buyer API responses."""
        return {
            "contract_version": self.contract_version,
            "project_key": self.project_key,
            "project_name": self.project_name,
            "focus_event_id": self.focus_event_id,
            "inference_status": self.inference_status,
            "participant_count": self.participant_count,
            "history_span_start": self.history_span_start,
            "history_span_end": self.history_span_end,
            "events": [event.to_wire() for event in self.events],
            "findings": [finding.to_wire() for finding in self.findings],
        }


def project_history_endpoint(transport_url: str) -> str:
    """Resolve TEPP's endpoint, permitting HTTP only for local loopback."""
    candidate = transport_url.strip()
    if not candidate:
        raise TeppProjectHistoryUnavailable("TEPP project-history transport is not configured")
    if any(ord(character) < 0x20 for character in candidate):
        raise TeppProjectHistoryUnavailable("TEPP project-history URL contains a control character")
    parsed = urlsplit(candidate)
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme != "https"
        and not (parsed.scheme == "http" and loopback)
    ) or not hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise TeppProjectHistoryUnavailable(
            "TEPP project-history URL must be HTTPS; HTTP is allowed only for loopback"
        )
    try:
        parsed.port
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable("TEPP project-history URL has an invalid port") from exc
    path = parsed.path.rstrip("/")
    if path.endswith("/v1/analysis-runs"):
        path = path[: -len("/v1/analysis-runs")]
    elif path and path != "/":
        raise TeppProjectHistoryUnavailable("TEPP transport URL has an unsupported path")
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}{PROJECT_HISTORY_PATH}", "", ""))


Transport = Callable[[str, dict[str, Any], dict[str, str], float], Any]


class TeppProjectHistoryClient:
    """Credential-free strict client for TEPP's project-history projection."""

    def __init__(
        self,
        transport_url: str,
        *,
        transport: Transport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._transport_url = transport_url
        self._transport = transport or self._post
        self._timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        """Return whether a syntactically valid TEPP endpoint is configured."""
        try:
            project_history_endpoint(self._transport_url)
        except TeppProjectHistoryUnavailable:
            return False
        return True

    @staticmethod
    def _post(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> Any:
        return post_json(url, payload, headers=headers, timeout=timeout)

    def project(self, request: ProjectHistoryRequest) -> ProjectHistoryProjection:
        """Submit one bounded request and validate TEPP's exact response."""
        url = project_history_endpoint(self._transport_url)
        payload = request.to_wire()
        headers = {
            "content-type": "application/json",
            "tepp-consumer": "lineageweave",
            "tepp-contract-version": str(PROJECT_HISTORY_CONTRACT_VERSION),
            "idempotency-key": request.idempotency_key,
        }
        try:
            response = self._transport(url, payload, headers, self._timeout_seconds)
        except (HttpClientError, OSError, TypeError, ValueError) as exc:
            raise TeppProjectHistoryUnavailable(str(exc)) from exc
        return ProjectHistoryProjection.from_wire(response, request=request)

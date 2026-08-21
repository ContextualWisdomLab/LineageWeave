"""Strict client contract for TEPP project-history validation.

LineageWeave owns authorization and selects exact project evidence. TEPP may
validate the bounded temporal sequence and return only coded, non-causal
findings over that evidence. Browser, reviewer, provider, and service
credentials never cross this boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from lineageweave.http_client import HttpClientError, post_json

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_PATH = "/v1/project-histories"
PROJECT_HISTORY_INFERENCE_STATUS = "temporal_association_only"
PROJECT_HISTORY_EVENT_LIMIT = 128
PROJECT_HISTORY_ACTOR_LIMIT = 64
PROJECT_HISTORY_FINDING_CODES = frozenset(
    {
        "contract_award_before_focus",
        "specification_change_before_focus",
        "delivery_before_focus",
        "handoff_before_focus",
        "rebid_after_focus",
        "specification_change_and_handoff_before_focus",
    }
)
_CODE_PATTERN = re.compile(r"^[a-z0-9_]+$")

Transport = Callable[[str, dict[str, Any], dict[str, str], float], Any]


class TeppProjectHistoryUnavailable(RuntimeError):
    """TEPP was absent or the project-history exchange could not complete."""


class TeppProjectHistoryInvalidResponse(TeppProjectHistoryUnavailable):
    """TEPP returned data outside the accepted public response contract."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    """Return one untrusted mapping or fail closed."""

    if not isinstance(value, Mapping):
        raise TeppProjectHistoryUnavailable(f"{name} must be an object")
    return value


def _closed_fields(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    """Require exactly one published field set."""

    if set(payload) != expected:
        raise TeppProjectHistoryUnavailable(f"{name} fields do not match the contract")


def _text(value: Any, name: str, maximum: int) -> str:
    """Return bounded non-empty text without control characters."""

    if not isinstance(value, str) or not value.strip():
        raise TeppProjectHistoryUnavailable(f"{name} must be non-empty text")
    if len(value.encode("utf-8")) > maximum or any(ord(char) < 0x20 for char in value):
        raise TeppProjectHistoryUnavailable(f"{name} exceeds its contract bound")
    return value.strip()


def _code(value: Any, name: str) -> str:
    """Return one bounded lower-snake code."""

    code = _text(value, name, 96)
    if not _CODE_PATTERN.fullmatch(code):
        raise TeppProjectHistoryUnavailable(f"{name} must be a lower-snake code")
    return code


def _timestamp(value: Any, name: str) -> datetime:
    """Parse one timezone-aware RFC 3339 timestamp as UTC."""

    raw = _text(value, name, 64)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable(f"{name} must be RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TeppProjectHistoryUnavailable(f"{name} must include an offset")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    """Serialize an aware clock as canonical UTC RFC 3339."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _opaque_actor_reference(workspace_id: str, actor_key: str) -> str:
    """Return one deterministic workspace-scoped pseudonymous actor reference."""

    digest = hashlib.sha256(f"{workspace_id}\x1f{actor_key}".encode()).hexdigest()
    return f"lw-actor-{digest}"


def _evidence_text(event: Mapping[str, Any]) -> str:
    """Build bounded evidence from persisted source-state fields only."""

    parts = [str(event.get("event_title") or "").strip()]
    for field_name in (
        "voc_type_code",
        "source_stage_code",
        "source_detail_state_code",
        "time_basis_code",
    ):
        value = event.get(field_name)
        if value is not None and str(value).strip():
            parts.append(f"{field_name}={str(value).strip()}")
    encoded = " | ".join(part for part in parts if part).encode("utf-8")
    if len(encoded) > 2_000:
        encoded = encoded[:2_000]
        while encoded:
            try:
                return encoded.decode("utf-8").rstrip()
            except UnicodeDecodeError:
                encoded = encoded[:-1]
    return encoded.decode("utf-8")


def build_tepp_project_history_request(
    *,
    projection: Mapping[str, Any],
    tenant_workspace_id: str,
) -> dict[str, Any]:
    """Translate one canonical LineageWeave projection into TEPP #159 input."""

    project_key = _text(projection.get("project_key"), "project_key", 256)
    project_name = _text(projection.get("project_name"), "project_name", 512)
    focus_event_id = _text(projection.get("focus_event_id"), "focus_event_id", 256)
    cutoff = _timestamp(projection.get("knowledge_cutoff"), "knowledge_cutoff")
    events_value = projection.get("events")
    if not isinstance(events_value, Sequence) or isinstance(events_value, (str, bytes)):
        raise TeppProjectHistoryUnavailable("events must be a list")
    if not events_value or len(events_value) > PROJECT_HISTORY_EVENT_LIMIT:
        raise TeppProjectHistoryUnavailable("event count is outside the contract bound")
    events: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for value in events_value:
        event = _mapping(value, "event")
        event_id = _text(event.get("event_id"), "event_id", 256)
        if event_id in event_ids:
            raise TeppProjectHistoryUnavailable("event identities must be unique")
        event_ids.add(event_id)
        occurred = _timestamp(event.get("occurred_at"), "occurred_at")
        if occurred > cutoff:
            raise TeppProjectHistoryUnavailable("event exceeds the knowledge cutoff")
        actor_values = event.get("responsibility_evidence") or event.get(
            "observed_responsibilities"
        ) or []
        if not isinstance(actor_values, Sequence) or isinstance(actor_values, (str, bytes)):
            raise TeppProjectHistoryUnavailable("responsibility evidence must be a list")
        actor_ids: list[str] = []
        for actor_value in actor_values:
            actor = _mapping(actor_value, "responsibility evidence")
            actor_key = _text(actor.get("actor_key"), "actor_key", 512)
            actor_reference = _opaque_actor_reference(tenant_workspace_id, actor_key)
            if actor_reference not in actor_ids:
                actor_ids.append(actor_reference)
        if len(actor_ids) > PROJECT_HISTORY_ACTOR_LIMIT:
            raise TeppProjectHistoryUnavailable("event actor count exceeds the contract bound")
        events.append(
            {
                "event_id": event_id,
                "event_type_code": _code(
                    event.get("event_type_code"), "event_type_code"
                ),
                "event_title": _text(event.get("event_title"), "event_title", 512),
                "occurred_at": _utc_text(occurred),
                "available_at": _utc_text(occurred),
                "source_post_id": _text(
                    event.get("source_post_id"), "source_post_id", 256
                ),
                "evidence_text": _text(_evidence_text(event), "evidence_text", 2_000),
                "actor_ids": actor_ids,
            }
        )
    if focus_event_id not in event_ids:
        raise TeppProjectHistoryUnavailable("focus event is outside the supplied bundle")
    events.sort(key=lambda event: (event["occurred_at"], event["event_id"]))
    identity_material = json.dumps(
        {
            "tenant_workspace_id": tenant_workspace_id,
            "project_key": project_key,
            "focus_event_id": focus_event_id,
            "knowledge_cutoff": _utc_text(cutoff),
            "event_ids": [event["event_id"] for event in events],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "idempotency_key": hashlib.sha256(identity_material.encode()).hexdigest(),
        "tenant_workspace_id": _text(
            tenant_workspace_id, "tenant_workspace_id", 256
        ),
        "project_key": project_key,
        "project_name": project_name,
        "knowledge_cutoff": _utc_text(cutoff),
        "focus_event_id": focus_event_id,
        "events": events,
    }


def validate_tepp_project_history_request(request: Any) -> dict[str, Any]:
    """Validate the exact outbound TEPP project-history request envelope."""

    payload = _mapping(request, "project-history request")
    expected = {
        "contract_version",
        "idempotency_key",
        "tenant_workspace_id",
        "project_key",
        "project_name",
        "knowledge_cutoff",
        "focus_event_id",
        "events",
    }
    _closed_fields(payload, expected, "project-history request")
    if payload["contract_version"] != PROJECT_HISTORY_CONTRACT_VERSION:
        raise TeppProjectHistoryUnavailable("unsupported request contract version")
    _text(payload["idempotency_key"], "idempotency_key", 256)
    _text(payload["tenant_workspace_id"], "tenant_workspace_id", 256)
    _text(payload["project_key"], "project_key", 256)
    _text(payload["project_name"], "project_name", 512)
    cutoff = _timestamp(payload["knowledge_cutoff"], "knowledge_cutoff")
    _text(payload["focus_event_id"], "focus_event_id", 256)
    events = payload["events"]
    if not isinstance(events, list) or not events or len(events) > PROJECT_HISTORY_EVENT_LIMIT:
        raise TeppProjectHistoryUnavailable("invalid event list")
    for event in events:
        event_payload = _mapping(event, "event")
        _closed_fields(
            event_payload,
            {
                "event_id",
                "event_type_code",
                "event_title",
                "occurred_at",
                "available_at",
                "source_post_id",
                "evidence_text",
                "actor_ids",
            },
            "event",
        )
        if _timestamp(event_payload["occurred_at"], "occurred_at") > cutoff:
            raise TeppProjectHistoryUnavailable("event exceeds cutoff")
        if _timestamp(event_payload["available_at"], "available_at") > cutoff:
            raise TeppProjectHistoryUnavailable("event availability exceeds cutoff")
    return dict(payload)


def _validate_finding(
    value: Any,
    *,
    event_ids: set[str],
    source_post_ids: set[str],
) -> dict[str, Any]:
    """Validate one finding against the exact authorized event bundle."""

    payload = _mapping(value, "finding")
    _closed_fields(
        payload,
        {"finding_code", "summary", "related_event_ids", "evidence_post_ids"},
        "finding",
    )
    related = payload["related_event_ids"]
    evidence = payload["evidence_post_ids"]
    if not isinstance(related, list) or not isinstance(evidence, list):
        raise TeppProjectHistoryUnavailable("finding references must be lists")
    related_ids = [_text(item, "related_event_id", 256) for item in related]
    evidence_ids = [_text(item, "evidence_post_id", 256) for item in evidence]
    if (
        not related_ids
        or not evidence_ids
        or len(related_ids) != len(set(related_ids))
        or len(evidence_ids) != len(set(evidence_ids))
        or not set(related_ids).issubset(event_ids)
        or not set(evidence_ids).issubset(source_post_ids)
    ):
        raise TeppProjectHistoryUnavailable("finding cites invalid evidence references")
    finding_code = _code(payload["finding_code"], "finding_code")
    if finding_code not in PROJECT_HISTORY_FINDING_CODES:
        raise TeppProjectHistoryUnavailable("finding code is outside the public vocabulary")
    return {
        "finding_code": finding_code,
        "summary": _text(payload["summary"], "finding summary", 4096),
        "related_event_ids": related_ids,
        "evidence_post_ids": evidence_ids,
    }


def validate_tepp_project_history_projection(
    value: Any,
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate TEPP output against the exact submitted evidence bundle."""

    payload = _mapping(value, "project-history response")
    expected = {
        "contract_version",
        "project_key",
        "project_name",
        "focus_event_id",
        "knowledge_cutoff",
        "history_span_start",
        "history_span_end",
        "participant_count",
        "inference_status",
        "events",
        "findings",
    }
    _closed_fields(payload, expected, "project-history response")
    if payload["contract_version"] != PROJECT_HISTORY_CONTRACT_VERSION:
        raise TeppProjectHistoryUnavailable("unsupported response contract version")
    if payload["inference_status"] != PROJECT_HISTORY_INFERENCE_STATUS:
        raise TeppProjectHistoryUnavailable("TEPP response exceeds its authority")
    for name in ("project_key", "project_name", "focus_event_id", "knowledge_cutoff"):
        if payload[name] != request[name]:
            raise TeppProjectHistoryUnavailable(f"TEPP changed {name}")
    response_events = payload["events"]
    if not isinstance(response_events, list) or response_events != request["events"]:
        raise TeppProjectHistoryUnavailable("TEPP changed supplied event evidence")
    ordered_events = sorted(
        response_events,
        key=lambda event: (_timestamp(event["occurred_at"], "occurred_at"), event["event_id"]),
    )
    if response_events != ordered_events:
        raise TeppProjectHistoryUnavailable("TEPP events are not deterministically ordered")
    start = _timestamp(payload["history_span_start"], "history_span_start")
    end = _timestamp(payload["history_span_end"], "history_span_end")
    if start != _timestamp(response_events[0]["occurred_at"], "occurred_at"):
        raise TeppProjectHistoryUnavailable("history start does not match evidence")
    if end != _timestamp(response_events[-1]["occurred_at"], "occurred_at"):
        raise TeppProjectHistoryUnavailable("history end does not match evidence")
    actors = {actor for event in response_events for actor in event["actor_ids"]}
    participant_count = payload["participant_count"]
    if (
        isinstance(participant_count, bool)
        or not isinstance(participant_count, int)
        or participant_count != len(actors)
    ):
        raise TeppProjectHistoryUnavailable("participant count is not evidence-derived")
    event_ids = {event["event_id"] for event in response_events}
    source_post_ids = {event["source_post_id"] for event in response_events}
    findings_value = payload["findings"]
    if not isinstance(findings_value, list):
        raise TeppProjectHistoryUnavailable("findings must be a list")
    findings = [
        _validate_finding(
            finding,
            event_ids=event_ids,
            source_post_ids=source_post_ids,
        )
        for finding in findings_value
    ]
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "project_key": payload["project_key"],
        "project_name": payload["project_name"],
        "focus_event_id": payload["focus_event_id"],
        "knowledge_cutoff": payload["knowledge_cutoff"],
        "history_span_start": _utc_text(start),
        "history_span_end": _utc_text(end),
        "participant_count": participant_count,
        "inference_status": PROJECT_HISTORY_INFERENCE_STATUS,
        "event_count": len(response_events),
        "findings": findings,
    }


def tepp_project_history_endpoint(transport_url: str) -> str:
    """Resolve TEPP's project endpoint, allowing HTTP only for loopback."""

    candidate = transport_url.strip()
    if not candidate or any(ord(char) < 0x20 for char in candidate):
        raise TeppProjectHistoryUnavailable("TEPP project-history URL is not configured")
    parsed = urlsplit(candidate)
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        (parsed.scheme != "https" and not (parsed.scheme == "http" and loopback))
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise TeppProjectHistoryUnavailable("TEPP URL must be HTTPS or loopback HTTP")
    try:
        parsed.port
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable("TEPP URL has an invalid port") from exc
    path = parsed.path.rstrip("/")
    if path.endswith("/v1/analysis-runs"):
        path = path[: -len("/v1/analysis-runs")]
    elif path.endswith(PROJECT_HISTORY_PATH):
        path = path[: -len(PROJECT_HISTORY_PATH)]
    elif path not in {"", "/"}:
        raise TeppProjectHistoryUnavailable("TEPP URL has an unsupported path")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"{path}{PROJECT_HISTORY_PATH}", "", "")
    )


class TeppProjectHistoryClient:
    """Submit a credential-free request and validate TEPP's exact response."""

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
        """Return whether a syntactically valid endpoint is configured."""

        try:
            tepp_project_history_endpoint(self._transport_url)
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
        """Post one bounded JSON exchange through the shared HTTP client."""

        return post_json(
            url,
            payload,
            headers=headers,
            timeout=timeout,
            include_llm_metadata=False,
        )

    def project(self, request: Any) -> dict[str, Any]:
        """Return a validated non-causal projection or fail closed."""

        target = tepp_project_history_endpoint(self._transport_url)
        payload = validate_tepp_project_history_request(request)
        headers = {
            "content-type": "application/json",
            "tepp-consumer": "lineageweave",
            "tepp-contract-version": str(PROJECT_HISTORY_CONTRACT_VERSION),
            "idempotency-key": payload["idempotency_key"],
        }
        try:
            response = self._transport(target, payload, headers, self._timeout_seconds)
        except TeppProjectHistoryUnavailable:
            raise
        except (HttpClientError, OSError, TypeError, ValueError) as exc:
            raise TeppProjectHistoryUnavailable("TEPP project-history request failed") from exc
        try:
            return validate_tepp_project_history_projection(response, request=payload)
        except TeppProjectHistoryUnavailable as exc:
            raise TeppProjectHistoryInvalidResponse(
                "TEPP project-history response violated its contract"
            ) from exc

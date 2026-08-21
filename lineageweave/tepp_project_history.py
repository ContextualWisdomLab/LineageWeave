"""Strict client for TEPP's cutoff-safe project-history projection.

LineageWeave owns authorization, exact project identity, and source selection.
TEPP may validate ordering and return temporal-association findings over that
closed evidence bundle. This module never forwards browser credentials, never
accepts changed source evidence, and never promotes order to causality.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .http_client import HttpClientError, post_json

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_PATH = "/v1/project-histories"
PROJECT_HISTORY_INFERENCE_STATUS = "temporal_association_only"
PROJECT_HISTORY_EVENT_LIMIT = 128
PROJECT_HISTORY_ACTOR_LIMIT = 64
PROJECT_HISTORY_BYTE_LIMIT = 256 * 1024
_RFC3339_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:"
    r"[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)

_REQUEST_FIELDS = frozenset(
    {
        "contract_version",
        "idempotency_key",
        "tenant_workspace_id",
        "project_key",
        "project_name",
        "knowledge_cutoff",
        "focus_event_id",
        "events",
    }
)
_EVENT_FIELDS = frozenset(
    {
        "event_id",
        "event_type_code",
        "event_title",
        "occurred_at",
        "available_at",
        "source_post_id",
        "evidence_text",
        "actor_ids",
    }
)
_PROJECTION_FIELDS = frozenset(
    {
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
)
_FINDING_FIELDS = frozenset(
    {"finding_code", "summary", "related_event_ids", "evidence_post_ids"}
)
_ALLOWED_FINDING_CODES = frozenset(
    {
        "contract_award_before_focus",
        "specification_change_before_focus",
        "delivery_before_focus",
        "handoff_before_focus",
        "rebid_after_focus",
        "specification_change_and_handoff_before_focus",
    }
)

Transport = Callable[[str, dict[str, Any], dict[str, str], float], Any]


class TeppProjectHistoryUnavailable(RuntimeError):
    """TEPP was absent or returned a response outside the public contract."""


class TeppProjectHistoryInvalidResponse(TeppProjectHistoryUnavailable):
    """TEPP returned a response that violated the validated evidence contract."""


def _exact_object(value: Any, fields: frozenset[str], name: str) -> Mapping[str, Any]:
    """Return a mapping only when it has the exact versioned field set."""

    if not isinstance(value, Mapping) or frozenset(value) != fields:
        raise TeppProjectHistoryUnavailable(f"{name} has invalid fields")
    return value


def _text(value: Any, name: str, maximum: int = 4096) -> str:
    """Return bounded, non-empty text without ASCII control characters."""

    if not isinstance(value, str):
        raise TeppProjectHistoryUnavailable(f"{name} must be text")
    normalized = value.strip()
    if (
        not normalized
        or len(normalized.encode("utf-8")) > maximum
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in normalized)
    ):
        raise TeppProjectHistoryUnavailable(f"{name} is empty or outside its bound")
    return normalized


def parse_rfc3339_utc(value: Any, name: str) -> tuple[datetime, str]:
    """Parse an RFC 3339 timestamp and return canonical UTC text."""

    raw = _text(value, name, 64)
    if _RFC3339_PATTERN.fullmatch(raw) is None:
        raise TeppProjectHistoryUnavailable(f"{name} is not RFC 3339")
    normalized_text = raw[:10] + "T" + raw[11:]
    try:
        parsed = datetime.fromisoformat(
            normalized_text[:-1] + "+00:00"
            if normalized_text.endswith(("Z", "z"))
            else normalized_text
        )
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable(f"{name} is not RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TeppProjectHistoryUnavailable(f"{name} must include an offset")
    utc = parsed.astimezone(timezone.utc)
    return utc, utc.isoformat().replace("+00:00", "Z")


def project_history_event_sort_key(event: Mapping[str, Any]) -> tuple[datetime, str]:
    """Order project-history events by their instant, then stable identity."""

    occurred_at, _ = parse_rfc3339_utc(event["occurred_at"], "occurred_at")
    return occurred_at, str(event["event_id"])


def _code(value: Any, name: str) -> str:
    """Return a bounded lower-snake contract code."""

    code = _text(value, name, 96)
    if not all(
        character.isascii()
        and (character.islower() or character.isdigit() or character == "_")
        for character in code
    ):
        raise TeppProjectHistoryUnavailable(f"{name} must be lower snake case")
    return code


def _event(value: Any, *, cutoff: datetime | None = None) -> dict[str, Any]:
    """Validate one exact source-grounded event."""

    payload = _exact_object(value, _EVENT_FIELDS, "project-history event")
    occurred, occurred_text = parse_rfc3339_utc(payload["occurred_at"], "occurred_at")
    available, available_text = parse_rfc3339_utc(payload["available_at"], "available_at")
    if cutoff is not None and (occurred > cutoff or available > cutoff):
        raise TeppProjectHistoryUnavailable("event exceeds the knowledge cutoff")
    raw_actors = payload["actor_ids"]
    if not isinstance(raw_actors, list) or len(raw_actors) > PROJECT_HISTORY_ACTOR_LIMIT:
        raise TeppProjectHistoryUnavailable("actor_ids must be a bounded list")
    actors = [_text(actor, "actor_id", 256) for actor in raw_actors]
    if len(actors) != len(set(actors)):
        raise TeppProjectHistoryUnavailable("actor_ids must be unique within an event")
    return {
        "event_id": _text(payload["event_id"], "event_id", 256),
        "event_type_code": _code(payload["event_type_code"], "event_type_code"),
        "event_title": _text(payload["event_title"], "event_title", 512),
        "occurred_at": occurred_text,
        "available_at": available_text,
        "source_post_id": _text(payload["source_post_id"], "source_post_id", 256),
        "evidence_text": _text(payload["evidence_text"], "evidence_text", 4096),
        "actor_ids": actors,
    }


def validate_tepp_project_history_request(
    value: Any,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and canonicalize one TEPP project-history request."""

    payload = _exact_object(value, _REQUEST_FIELDS, "project-history request")
    if payload["contract_version"] != PROJECT_HISTORY_CONTRACT_VERSION:
        raise TeppProjectHistoryUnavailable("unsupported request contract version")
    receipt = now or datetime.now(timezone.utc)
    if receipt.tzinfo is None or receipt.utcoffset() is None:
        raise TeppProjectHistoryUnavailable("request receipt clock must be offset-aware")
    cutoff, cutoff_text = parse_rfc3339_utc(payload["knowledge_cutoff"], "knowledge_cutoff")
    if cutoff > receipt.astimezone(timezone.utc):
        raise TeppProjectHistoryUnavailable("knowledge cutoff is after request receipt")
    raw_events = payload["events"]
    if (
        not isinstance(raw_events, list)
        or not raw_events
        or len(raw_events) > PROJECT_HISTORY_EVENT_LIMIT
    ):
        raise TeppProjectHistoryUnavailable("event count is outside the contract bound")
    events = [_event(event, cutoff=cutoff) for event in raw_events]
    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise TeppProjectHistoryUnavailable("event identities must be unique")
    focus_event_id = _text(payload["focus_event_id"], "focus_event_id", 256)
    if focus_event_id not in set(event_ids):
        raise TeppProjectHistoryUnavailable("focus event is outside the evidence bundle")
    validated = {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "idempotency_key": _text(payload["idempotency_key"], "idempotency_key", 256),
        "tenant_workspace_id": _text(
            payload["tenant_workspace_id"], "tenant_workspace_id", 256
        ),
        "project_key": _text(payload["project_key"], "project_key", 256),
        "project_name": _text(payload["project_name"], "project_name", 512),
        "knowledge_cutoff": cutoff_text,
        "focus_event_id": focus_event_id,
        "events": events,
    }
    wire = json.dumps(validated, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(wire) > PROJECT_HISTORY_BYTE_LIMIT:
        raise TeppProjectHistoryUnavailable("project-history request exceeds 256 KiB")
    return validated


def _finding(
    value: Any,
    *,
    event_ids: set[str],
    source_post_ids: set[str],
) -> dict[str, Any]:
    """Validate one finding against the submitted evidence bundle."""

    payload = _exact_object(value, _FINDING_FIELDS, "project-history finding")
    related = payload["related_event_ids"]
    evidence = payload["evidence_post_ids"]
    if not isinstance(related, list) or not isinstance(evidence, list):
        raise TeppProjectHistoryUnavailable("finding references must be lists")
    related_ids = [_text(item, "related_event_id", 256) for item in related]
    evidence_ids = [_text(item, "evidence_post_id", 256) for item in evidence]
    if (
        not related_ids
        or not evidence_ids
        or not set(related_ids).issubset(event_ids)
        or not set(evidence_ids).issubset(source_post_ids)
    ):
        raise TeppProjectHistoryUnavailable("finding cites evidence outside the bundle")
    finding_code = _code(payload["finding_code"], "finding_code")
    if finding_code not in _ALLOWED_FINDING_CODES:
        raise TeppProjectHistoryUnavailable("finding code is not in the published vocabulary")
    if len(related_ids) != len(set(related_ids)) or len(evidence_ids) != len(
        set(evidence_ids)
    ):
        raise TeppProjectHistoryUnavailable("finding references must be unique")
    return {
        "finding_code": finding_code,
        "summary": _text(payload["summary"], "finding summary", 4096),
        "related_event_ids": related_ids,
        "evidence_post_ids": evidence_ids,
    }


def validate_tepp_project_history_projection(
    value: Any,
    *,
    request: Any,
) -> dict[str, Any]:
    """Validate TEPP output against the exact submitted events and identities."""

    validated_request = validate_tepp_project_history_request(request)
    payload = _exact_object(value, _PROJECTION_FIELDS, "project-history projection")
    if payload["contract_version"] != PROJECT_HISTORY_CONTRACT_VERSION:
        raise TeppProjectHistoryUnavailable("unsupported response contract version")
    if payload["inference_status"] != PROJECT_HISTORY_INFERENCE_STATUS:
        raise TeppProjectHistoryUnavailable("TEPP response attempted causal authority")
    if (
        _text(payload["project_key"], "project_key", 256)
        != validated_request["project_key"]
        or _text(payload["project_name"], "project_name", 512)
        != validated_request["project_name"]
        or _text(payload["focus_event_id"], "focus_event_id", 256)
        != validated_request["focus_event_id"]
    ):
        raise TeppProjectHistoryUnavailable("TEPP changed project or focus identity")
    _, response_cutoff = parse_rfc3339_utc(payload["knowledge_cutoff"], "knowledge_cutoff")
    if response_cutoff != validated_request["knowledge_cutoff"]:
        raise TeppProjectHistoryUnavailable("TEPP changed the knowledge cutoff")
    raw_events = payload["events"]
    if not isinstance(raw_events, list):
        raise TeppProjectHistoryUnavailable("projection events must be a list")
    response_events = [_event(event) for event in raw_events]
    expected_events = sorted(
        validated_request["events"],
        key=project_history_event_sort_key,
    )
    if response_events != expected_events:
        raise TeppProjectHistoryUnavailable("TEPP changed or reordered supplied evidence")
    participant_count = payload["participant_count"]
    expected_participants = len(
        {actor for event in response_events for actor in event["actor_ids"]}
    )
    if (
        isinstance(participant_count, bool)
        or not isinstance(participant_count, int)
        or participant_count != expected_participants
    ):
        raise TeppProjectHistoryUnavailable("participant count is not evidence-derived")
    _, span_start = parse_rfc3339_utc(payload["history_span_start"], "history_span_start")
    _, span_end = parse_rfc3339_utc(payload["history_span_end"], "history_span_end")
    if (
        span_start != response_events[0]["occurred_at"]
        or span_end != response_events[-1]["occurred_at"]
    ):
        raise TeppProjectHistoryUnavailable("history span does not match ordered events")
    raw_findings = payload["findings"]
    if not isinstance(raw_findings, list):
        raise TeppProjectHistoryUnavailable("projection findings must be a list")
    event_ids = {event["event_id"] for event in response_events}
    source_post_ids = {event["source_post_id"] for event in response_events}
    findings = [
        _finding(
            finding,
            event_ids=event_ids,
            source_post_ids=source_post_ids,
        )
        for finding in raw_findings
    ]
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "project_key": validated_request["project_key"],
        "project_name": validated_request["project_name"],
        "focus_event_id": validated_request["focus_event_id"],
        "knowledge_cutoff": response_cutoff,
        "history_span_start": span_start,
        "history_span_end": span_end,
        "participant_count": participant_count,
        "inference_status": PROJECT_HISTORY_INFERENCE_STATUS,
        "events": response_events,
        "findings": findings,
    }


def tepp_project_history_endpoint(transport_url: str) -> str:
    """Resolve the project-history URL, allowing plain HTTP only on loopback."""

    candidate = transport_url.strip()
    if not candidate or any(ord(character) < 0x20 for character in candidate):
        raise TeppProjectHistoryUnavailable("TEPP project-history transport is not configured")
    parsed = urlsplit(candidate)
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not hostname
        or (parsed.scheme != "https" and not (parsed.scheme == "http" and loopback))
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
            maximum_response_bytes=PROJECT_HISTORY_BYTE_LIMIT,
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
        except Exception as exc:
            raise TeppProjectHistoryUnavailable("TEPP project-history request failed") from exc
        try:
            return validate_tepp_project_history_projection(response, request=payload)
        except TeppProjectHistoryUnavailable as exc:
            raise TeppProjectHistoryInvalidResponse(
                "TEPP project-history response violated its contract"
            ) from exc

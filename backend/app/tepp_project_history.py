"""Map the canonical Buyer project history into TEPP's strict wire contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    TeppProjectHistoryClient,
    TeppProjectHistoryUnavailable,
    validate_tepp_project_history_request,
)


def tenant_workspace_reference(corporate_entity_ids: Iterable[str]) -> str:
    """Return a deterministic opaque workspace reference for the ABAC scope."""

    normalized = sorted({str(value).strip() for value in corporate_entity_ids if str(value).strip()})
    material = "\u001f".join(normalized) if normalized else "public-only"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"lw-workspace-{digest}"


def _utc_text(value: object, field_name: str) -> str:
    """Return canonical UTC text from one offset-aware source timestamp."""

    if not isinstance(value, str) or not value.strip():
        raise TeppProjectHistoryUnavailable(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TeppProjectHistoryUnavailable(f"{field_name} is not ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TeppProjectHistoryUnavailable(f"{field_name} must include an offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _opaque_actor_ids(
    event: Mapping[str, Any],
    *,
    tenant_workspace_id: str,
) -> list[str]:
    """Hash canonical actor keys so names and local identifiers do not cross."""

    raw_roles = event.get("responsibility_evidence")
    if raw_roles is None:
        raw_roles = event.get("observed_responsibilities")
    if not isinstance(raw_roles, Sequence) or isinstance(raw_roles, (str, bytes)):
        raw_roles = ()
    actor_ids: set[str] = set()
    for role in raw_roles:
        if not isinstance(role, Mapping):
            continue
        actor_key = str(role.get("actor_key") or "").strip()
        if not actor_key:
            continue
        material = f"{tenant_workspace_id}\u0000{actor_key}".encode("utf-8")
        actor_ids.add(f"lw-actor-{hashlib.sha256(material).hexdigest()}")
    return sorted(actor_ids)


def _evidence_text(event: Mapping[str, Any]) -> str:
    """Build bounded source-field evidence without sending a post body."""

    title = str(event.get("event_title") or "").strip()
    event_type = str(event.get("event_type_code") or "").strip()
    if not title or not event_type:
        raise TeppProjectHistoryUnavailable("canonical event title and type are required")
    parts = [title, f"event_type={event_type}"]
    for key in ("source_stage_code", "source_detail_state_code", "voc_type_code"):
        value = str(event.get(key) or "").strip()
        if value:
            parts.append(f"{key}={value}")
    rendered = " | ".join(parts)
    encoded = rendered.encode("utf-8")
    if len(encoded) <= 4096:
        return rendered
    return encoded[:4096].decode("utf-8", errors="ignore").rstrip()


def _idempotency_key(request_without_key: Mapping[str, Any]) -> str:
    """Hash the exact authorized evidence bundle into a stable request key."""

    material = json.dumps(
        request_without_key,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"lineageweave-project-history-{digest}"


def build_tepp_project_history_request(
    *,
    projection: Mapping[str, Any],
    tenant_workspace_id: str,
) -> dict[str, Any]:
    """Build TEPP #159 input from the already-authorized canonical timeline."""

    if projection.get("contract_version") != 1:
        raise TeppProjectHistoryUnavailable("unsupported canonical project-history version")
    events_value = projection.get("events")
    if not isinstance(events_value, Sequence) or isinstance(events_value, (str, bytes)):
        raise TeppProjectHistoryUnavailable("canonical project history has no event list")
    cutoff = _utc_text(projection.get("knowledge_cutoff"), "knowledge_cutoff")
    events: list[dict[str, Any]] = []
    for value in events_value:
        if not isinstance(value, Mapping):
            raise TeppProjectHistoryUnavailable("canonical project event must be an object")
        occurred_at = _utc_text(value.get("occurred_at"), "occurred_at")
        event_id = str(value.get("event_id") or "").strip()
        source_post_id = str(value.get("source_post_id") or "").strip()
        if not event_id or not source_post_id:
            raise TeppProjectHistoryUnavailable("canonical project event identity is missing")
        events.append(
            {
                "event_id": event_id,
                "event_type_code": str(value.get("event_type_code") or "").strip(),
                "event_title": str(value.get("event_title") or "").strip(),
                "occurred_at": occurred_at,
                # The canonical timeline explicitly declares source-post creation
                # time as its fallback clock. It is therefore also the earliest
                # evidence-availability instant LineageWeave can substantiate.
                "available_at": occurred_at,
                "source_post_id": source_post_id,
                "evidence_text": _evidence_text(value),
                "actor_ids": _opaque_actor_ids(
                    value,
                    tenant_workspace_id=tenant_workspace_id,
                ),
            }
        )
    events.sort(key=lambda event: (event["occurred_at"], event["event_id"]))
    request: dict[str, Any] = {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "tenant_workspace_id": tenant_workspace_id,
        "project_key": str(projection.get("project_key") or "").strip(),
        "project_name": str(projection.get("project_name") or "").strip(),
        "knowledge_cutoff": cutoff,
        "focus_event_id": str(projection.get("focus_event_id") or "").strip(),
        "events": events,
    }
    request["idempotency_key"] = _idempotency_key(request)
    return validate_tepp_project_history_request(request)


def _buyer_metadata(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Strip duplicate event rows while preserving TEPP findings and evidence IDs."""

    events = projection["events"]
    return {
        "contract_version": projection["contract_version"],
        "project_key": projection["project_key"],
        "project_name": projection["project_name"],
        "focus_event_id": projection["focus_event_id"],
        "knowledge_cutoff": projection["knowledge_cutoff"],
        "history_span_start": projection["history_span_start"],
        "history_span_end": projection["history_span_end"],
        "participant_count": projection["participant_count"],
        "inference_status": projection["inference_status"],
        "event_count": len(events),
        "findings": projection["findings"],
    }


def validate_project_history_with_tepp(
    *,
    projection: Mapping[str, Any],
    tenant_workspace_id: str,
    transport_url: str,
) -> dict[str, Any]:
    """Return optional TEPP metadata without hiding the canonical timeline."""

    if not transport_url.strip():
        return {
            "status": "not_configured",
            "project_history": None,
            "next_action_code": "configure_tepp_project_history",
        }
    try:
        request = build_tepp_project_history_request(
            projection=projection,
            tenant_workspace_id=tenant_workspace_id,
        )
    except TeppProjectHistoryUnavailable:
        return {
            "status": "invalid_evidence",
            "project_history": None,
            "next_action_code": "open_source_evidence",
        }
    try:
        validated = TeppProjectHistoryClient(transport_url).project(request)
    except TeppProjectHistoryUnavailable:
        return {
            "status": "unavailable",
            "project_history": None,
            "next_action_code": "retry_tepp_project_history",
        }
    return {
        "status": "validated",
        "project_history": _buyer_metadata(validated),
        "next_action_code": "open_source_evidence",
    }

"""Authorized LineageWeave evidence adapter for TEPP project histories."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import asyncpg

from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    ProjectHistoryEvent,
    ProjectHistoryRequest,
    TeppProjectHistoryClient,
    TeppProjectHistoryUnavailable,
)

# Only explicit persisted lifecycle codes are promoted into the closed TEPP
# event vocabulary. Unknown codes stay observed evidence, never guessed stages.
_STAGE_EVENT_TYPES = {
    "contract_awarded": "contract_awarded",
    "award": "contract_awarded",
    "order_received": "contract_awarded",
    "order_won": "contract_awarded",
    "sow_signed": "contract_awarded",
    "specification_changed": "specification_changed",
    "spec_change": "specification_changed",
    "design_change": "specification_changed",
    "requirements_changed": "specification_changed",
    "delivered": "delivered",
    "delivery": "delivered",
    "handoff": "operational_handoff",
    "operational_handoff": "operational_handoff",
    "go_live": "operational_handoff",
    "voc_received": "voc_received",
    "voc": "voc_received",
    "rebid_started": "rebid_started",
    "rebid": "rebid_started",
    "retender": "rebid_started",
    "tender": "rebid_started",
}
_VOC_CODES = {"voc", "voice_of_customer", "customer_complaint", "complaint"}


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stage_event_type(stage_code: Any, voc_type_code: Any) -> str:
    stage = str(stage_code or "").strip().casefold()
    voc = str(voc_type_code or "").strip().casefold()
    if voc in _VOC_CODES:
        return "voc_received"
    return _STAGE_EVENT_TYPES.get(stage, "event_observed")


def _evidence_excerpt(row: Mapping[str, Any]) -> str:
    value = str(row.get("post_body_excerpt") or row.get("post_body") or "").strip()
    if not value:
        value = str(row.get("post_title") or "Observed project event").strip()
    encoded = value.encode("utf-8")
    if len(encoded) <= 2_000:
        return value
    return encoded[:2_000].decode("utf-8", errors="ignore").rstrip()


def _idempotency_key(
    *,
    tenant_workspace_id: str,
    project_key: str,
    focus_post_id: str,
    knowledge_cutoff: datetime,
    post_ids: Sequence[str],
) -> str:
    material = json.dumps(
        {
            "tenant_workspace_id": tenant_workspace_id,
            "project_key": project_key,
            "focus_post_id": focus_post_id,
            "knowledge_cutoff": _utc_text(knowledge_cutoff),
            "post_ids": sorted(set(post_ids)),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"lineageweave-project-history-{hashlib.sha256(material.encode()).hexdigest()}"


def build_project_history_request(
    *,
    rows: Sequence[Mapping[str, Any]],
    tenant_workspace_id: str,
    focus_post_id: str,
    knowledge_cutoff: datetime,
    idempotency_key: str | None = None,
) -> ProjectHistoryRequest | None:
    """Build one exact-project request from already authorized source rows.

    Rows from another project, rows unavailable at the cutoff, and rows without
    an explicit project code are excluded.  The function never guesses a
    project from lexical similarity and never invents a missing lifecycle event.
    """
    focus = next((row for row in rows if str(row.get("post_id")) == focus_post_id), None)
    if focus is None:
        return None
    project_key = str(focus.get("source_project_code") or "").strip()
    project_name = str(focus.get("source_project_name") or project_key).strip()
    if not project_key or not project_name:
        return None
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    cutoff = cutoff.astimezone(timezone.utc)
    events: list[ProjectHistoryEvent] = []
    for row in rows:
        if str(row.get("source_project_code") or "").strip() != project_key:
            continue
        created_at = row.get("created_at")
        if not isinstance(created_at, datetime):
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_at = created_at.astimezone(timezone.utc)
        if created_at > cutoff:
            continue
        post_id = str(row.get("post_id") or "").strip()
        title = str(row.get("post_title") or "").strip()
        if not post_id or not title:
            continue
        raw_actor_ids = row.get("actor_ids") or (row.get("author_actor_id"),)
        actor_ids = tuple(str(value) for value in raw_actor_ids if value)
        events.append(
            ProjectHistoryEvent(
                event_id=post_id,
                event_type_code=_stage_event_type(
                    row.get("source_stage_code"), row.get("voc_type_code")
                ),
                event_title=title,
                event_time=_utc_text(created_at),
                available_at=_utc_text(created_at),
                availability_basis="source_post.created_at",
                source_post_id=post_id,
                evidence_text=_evidence_excerpt(row),
                actor_ids=actor_ids,
            )
        )
    if not events or focus_post_id not in {event.event_id for event in events}:
        return None
    events.sort(key=lambda event: (event.event_time, event.event_id))
    key = idempotency_key or _idempotency_key(
        tenant_workspace_id=tenant_workspace_id,
        project_key=project_key,
        focus_post_id=focus_post_id,
        knowledge_cutoff=cutoff,
        post_ids=[event.source_post_id for event in events],
    )
    return ProjectHistoryRequest(
        contract_version=PROJECT_HISTORY_CONTRACT_VERSION,
        idempotency_key=key,
        tenant_workspace_id=tenant_workspace_id,
        project_key=project_key,
        project_name=project_name,
        knowledge_cutoff=_utc_text(cutoff),
        focus_event_id=focus_post_id,
        events=tuple(events),
    )


async def _load_project_rows(
    conn: asyncpg.Connection,
    *,
    focus_post_id: str,
    source_post_ids: Sequence[str],
    corporate_entity_ids: Iterable[str],
    knowledge_cutoff: datetime,
) -> list[Mapping[str, Any]]:
    """Load a bounded, ABAC-visible exact-project history around one focus post.

    The cited/source IDs are prioritization hints, not a retrieval boundary. A
    reader opening one VOC must still receive earlier contract, specification,
    delivery, and handoff evidence from the same authorized project. The focus
    and cited rows are kept ahead of other history when the 128-event safety
    bound is reached; Python later restores strict chronological order.
    """
    focus = await conn.fetchrow(
        """
        select post_id, source_project_code, source_project_name
          from source_post
         where post_id = $1::uuid
        """,
        focus_post_id,
    )
    if focus is None or not str(focus["source_project_code"] or "").strip():
        return []
    project_key = str(focus["source_project_code"]).strip()
    preferred_ids = list(dict.fromkeys([focus_post_id, *source_post_ids]))
    rows = await conn.fetch(
        """
        select post.post_id,
               post.post_title,
               post.source_stage_code,
               post.voc_type_code,
               post.source_project_code,
               post.source_project_name,
               post.post_body,
               post.created_at,
               post.author_account_id::text as author_actor_id
          from source_post post
         where post.source_project_code = $1
           and post.created_at <= $4
           and (
               post.visibility_code = 'public'
               or post.corporate_entity_id::text = any($5::text[])
           )
         order by
               case when post.post_id = $2::uuid then 0 else 1 end,
               case when array_position($3::uuid[], post.post_id) is not null then 0 else 1 end,
               post.created_at desc,
               post.post_id
         limit 128
        """,
        project_key,
        focus_post_id,
        preferred_ids,
        knowledge_cutoff,
        [str(value) for value in corporate_entity_ids],
    )
    return [
        {
            **dict(row),
            "post_body_excerpt": _evidence_excerpt(dict(row)),
        }
        for row in rows
    ]


async def project_history_for_post_ids(
    conn: asyncpg.Connection,
    *,
    tenant_workspace_id: str,
    corporate_entity_ids: Iterable[str],
    focus_post_id: str,
    source_post_ids: Sequence[str],
    knowledge_cutoff: datetime,
    tepp_transport_url: str,
) -> dict[str, Any]:
    """Return a typed buyer envelope for one TEPP project-history projection."""
    client = TeppProjectHistoryClient(tepp_transport_url)
    if not client.available:
        return {
            "status": "tepp_unavailable",
            "project_history": None,
            "next_action": "Configure the TEPP HTTPS project-history endpoint.",
        }
    rows = await _load_project_rows(
        conn,
        focus_post_id=focus_post_id,
        source_post_ids=source_post_ids,
        corporate_entity_ids=corporate_entity_ids,
        knowledge_cutoff=knowledge_cutoff,
    )
    request = build_project_history_request(
        rows=rows,
        tenant_workspace_id=tenant_workspace_id,
        focus_post_id=focus_post_id,
        knowledge_cutoff=knowledge_cutoff,
    )
    if request is None:
        return {
            "status": "insufficient_project_evidence",
            "project_history": None,
            "next_action": "Open a post with an explicit project code and authorized history evidence.",
        }
    try:
        projection = client.project(request)
    except TeppProjectHistoryUnavailable:
        return {
            "status": "tepp_unavailable",
            "project_history": None,
            "next_action": "Retry after the TEPP project-history service is available.",
        }
    return {
        "status": "available",
        "project_history": projection.to_wire(),
        "next_action": "Open a timeline event to inspect its exact source post.",
    }

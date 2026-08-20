"""Select authorized project evidence and build TEPP history requests.

The database remains authoritative for post visibility and source metadata.
This module sends only bounded event labels, evidence excerpts, opaque post and
actor references, project identity, and clocks. It does not send a raw body,
provider credential, score, or causal conclusion.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    ProjectHistoryEvent,
    ProjectHistoryRequest,
)

_EVENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rebid_started", ("rebid", "re-bid", "retender", "re-tender", "재입찰")),
    (
        "handoff_recorded",
        ("handoff", "hand-off", "transferred ownership", "operational transfer", "인수인계"),
    ),
    (
        "specification_changed",
        (
            "specification change",
            "specification revision",
            "revised specification",
            "spec revision",
            "사양 변경",
            "사양변경",
        ),
    ),
    (
        "delivered",
        (
            "delivery confirmed",
            "delivery completed",
            "delivered",
            "shipment completed",
            "납품 완료",
            "납품완료",
        ),
    ),
    (
        "contract_awarded",
        (
            "contract awarded",
            "award confirmed",
            "order confirmation",
            "purchase order received",
            "수주 확정",
            "수주확정",
        ),
    ),
)
_VOC_CODES = frozenset({"voc", "vocc", "voco", "vom", "vop"})


def classify_event_type(
    post_title: str,
    source_stage_code: str | None,
    source_detail_state_code: str | None,
    voc_type_code: str | None,
    is_focus: bool,
) -> str:
    """Map explicit structured/title evidence to TEPP's bounded event vocabulary.

    A generic VOC-family row is not automatically another VOC event. Only the
    focused row gets that fallback; non-focus rows require explicit event
    language and otherwise remain ``source_recorded``.
    """
    text = " ".join(
        value.strip().casefold()
        for value in (post_title, source_stage_code or "", source_detail_state_code or "")
        if value.strip()
    )
    for event_type_code, patterns in _EVENT_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return event_type_code
    if is_focus and (voc_type_code or "").casefold() in _VOC_CODES:
        return "voc_received"
    return "source_recorded"


def _as_utc_rfc3339(value: datetime) -> str:
    """Serialize one aware or assumed-UTC datetime as canonical UTC text."""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_evidence(value: object, fallback: str) -> str:
    """Return a compact evidence excerpt without forwarding raw source bodies."""
    text = str(value or "").strip() or fallback.strip()
    encoded = text.encode("utf-8")
    if len(encoded) <= 4096:
        return text
    return encoded[:4096].decode("utf-8", errors="ignore").rstrip()


def _project_identity(focus: Mapping[str, Any]) -> tuple[str, str]:
    """Choose a stable existing project identity without inventing one."""
    project_code = str(focus.get("source_project_code") or "").strip()
    project_name = str(focus.get("source_project_name") or "").strip()
    grouping_key = str(focus.get("secondary_grouping_key") or "").strip()
    if project_code:
        return project_code, project_name or project_code
    if grouping_key:
        return grouping_key, project_name or grouping_key
    post_id = str(focus["post_id"])
    return f"post:{post_id}", project_name or str(focus["post_title"])


def build_project_history_request(
    rows: Sequence[Mapping[str, Any]],
    *,
    focus_post_id: str,
    tenant_workspace_id: str,
    knowledge_cutoff: datetime,
) -> ProjectHistoryRequest:
    """Build the exact TEPP request from already-authorized source rows.

    Raises:
        ValueError: no focus row exists, the cutoff excludes an event, or the
            selected rows do not share the focus project's explicit identity.
    """
    focus_rows = [row for row in rows if str(row["post_id"]) == focus_post_id]
    if len(focus_rows) != 1:
        raise ValueError("project history requires one visible focus post")
    focus = focus_rows[0]
    project_key, project_name = _project_identity(focus)
    cutoff = knowledge_cutoff if knowledge_cutoff.tzinfo is not None else knowledge_cutoff.replace(
        tzinfo=timezone.utc
    )
    cutoff = cutoff.astimezone(timezone.utc)

    events: list[ProjectHistoryEvent] = []
    for row in sorted(rows, key=lambda item: (item["created_at"], str(item["post_id"]))):
        event_time = row["created_at"]
        if not isinstance(event_time, datetime):
            raise ValueError("project-history event time must be a datetime")
        event_time_utc = (
            event_time if event_time.tzinfo is not None else event_time.replace(tzinfo=timezone.utc)
        ).astimezone(timezone.utc)
        if event_time_utc > cutoff:
            raise ValueError("project-history evidence is after the knowledge cutoff")
        actor_ids = tuple(
            sorted({str(value).strip() for value in row.get("actor_ids", ()) if str(value).strip()})
        )
        post_id = str(row["post_id"])
        title = str(row["post_title"])
        events.append(
            ProjectHistoryEvent(
                event_id=post_id,
                event_type_code=classify_event_type(
                    title,
                    row.get("source_stage_code"),
                    row.get("source_detail_state_code"),
                    row.get("voc_type_code"),
                    post_id == focus_post_id,
                ),
                event_title=title,
                occurred_at=_as_utc_rfc3339(event_time_utc),
                available_at=_as_utc_rfc3339(event_time_utc),
                availability_basis_code="source_created_at_proxy",
                source_post_id=post_id,
                evidence_text=_bounded_evidence(row.get("evidence_text"), title),
                actor_ids=actor_ids,
            )
        )
    if not events:
        raise ValueError("project history has no authorized events")

    digest_material = "\u001f".join(
        [tenant_workspace_id, project_key, _as_utc_rfc3339(cutoff), *(event.event_id for event in events)]
    )
    idempotency_key = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()
    return ProjectHistoryRequest(
        contract_version=PROJECT_HISTORY_CONTRACT_VERSION,
        idempotency_key=idempotency_key,
        tenant_workspace_id=tenant_workspace_id,
        project_key=project_key,
        project_name=project_name,
        knowledge_cutoff=_as_utc_rfc3339(cutoff),
        focus_event_id=focus_post_id,
        events=tuple(events),
    )


async def fetch_project_history_rows(
    conn: asyncpg.Connection,
    *,
    focus_post_id: str,
    knowledge_cutoff: datetime,
    can_see: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Load a bounded, project-coherent, ABAC-visible source evidence set."""
    # Safe SQL: the eligibility predicate and alias are immutable module constants; post id is bound.
    focus = await conn.fetchrow(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, post_body, voc_type_code, visibility_code,
               corporate_entity_id, created_at, source_stage_code,
               source_detail_state_code, source_project_code, source_project_name,
               secondary_grouping_key
        from source_post
        where post_id = $1
          and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}
        """,
        focus_post_id,
    )
    if focus is None or not can_see(focus):
        return []
    project_code = str(focus["source_project_code"] or "").strip() or None
    grouping_key = str(focus["secondary_grouping_key"] or "").strip() or None
    # Safe SQL: the eligibility predicate and alias are immutable module constants; all values are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id, post.post_title, post.voc_type_code,
               post.visibility_code, post.corporate_entity_id, post.created_at,
               post.source_stage_code, post.source_detail_state_code,
               post.source_project_code, post.source_project_name,
               post.secondary_grouping_key,
               coalesce(
                   (select string_agg(event.event_text, '; ' order by event.event_ordinal)
                    from post_summary_event event where event.post_id = post.post_id),
                   btrim(left(source_post_search_text(post.post_body), 1000)),
                   post.post_title
               ) as evidence_text
        from source_post post
        where post.created_at <= $2
          and (
              post.post_id = $1
              or ($3::text is not null and post.source_project_code = $3)
              or ($4::text is not null and post.secondary_grouping_key = $4)
          )
          and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
        order by post.created_at, post.post_id
        limit 128
        """,
        focus_post_id,
        knowledge_cutoff,
        project_code,
        grouping_key,
    )
    visible = [dict(row) for row in rows if can_see(row)]
    post_ids = [row["post_id"] for row in visible]
    actor_map: dict[str, list[str]] = {str(post_id): [] for post_id in post_ids}
    if post_ids:
        actor_rows = await conn.fetch(
            """
            select post_id, cataloged_person_id
            from post_summary_role
            where post_id = any($1::uuid[])
              and cataloged_person_id is not null
            order by post_id, cataloged_person_id
            """,
            post_ids,
        )
        for actor_row in actor_rows:
            actor_map[str(actor_row["post_id"])].append(str(actor_row["cataloged_person_id"]))
    for row in visible:
        row["actor_ids"] = actor_map.get(str(row["post_id"]), [])
        row["is_focus"] = str(row["post_id"]) == focus_post_id
    return visible

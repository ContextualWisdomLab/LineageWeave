"""Build evidence-bound project histories from already-authorized rows.

The module is deliberately storage-agnostic. Callers must apply RBAC, ABAC,
source eligibility, and knowledge-cutoff filtering before invoking it. It then
orders visible source records, keeps explicit and semantic project matches
separate, projects observed responsibility evidence, and explains persisted
lineage paths without promoting them to causal or authoritative facts.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unicodedata import normalize

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_TIME_BASIS = "document_time"
PROJECT_HISTORY_MAX_DEPTH = 8
PROJECT_HISTORY_MAX_PATHS_PER_EVENT = 32

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


def normalize_project_key(value: str) -> str:
    """Return the exact project-identity comparison key.

    Compatibility normalization lets full-width and compatibility forms match
    while preserving a deterministic, locale-neutral lower-case comparison.
    Empty values are rejected rather than becoming a match-all key.
    """

    normalized = normalize("NFKC", value).strip().lower()
    if not normalized:
        raise ValueError("project key must not be empty")
    if len(normalized.encode("utf-8")) > 256:
        raise ValueError("project key exceeds 256 UTF-8 bytes")
    return normalized


def classify_project_event(
    *,
    title: str,
    source_stage_code: str | None,
    source_detail_state_code: str | None,
    voc_type_code: str | None,
    is_focus: bool,
) -> str:
    """Classify a display event from explicit source text and codes.

    The code is presentation metadata only. It never creates a new event or
    changes the truth status of the source record.
    """

    text = " ".join(
        part.strip().lower()
        for part in (title, source_stage_code or "", source_detail_state_code or "")
        if part.strip()
    )
    for event_code, patterns in _EVENT_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return event_code
    if is_focus and (voc_type_code or "").strip().lower() in _VOC_CODES:
        return "voc_received"
    return "source_recorded"


def responsibility_transition_code(
    previous_actor_keys: Sequence[str], current_actor_keys: Sequence[str]
) -> str:
    """Classify adjacent observed responsibility evidence.

    Missing evidence on either event is an ``assignment_gap``. Equal non-empty
    actor sets are ``continuous``; different non-empty sets are ``handoff``.
    The result describes document evidence, not an HR assignment fact.
    """

    previous = frozenset(key for key in previous_actor_keys if key)
    current = frozenset(key for key in current_actor_keys if key)
    if not previous or not current:
        return "assignment_gap"
    if previous == current:
        return "continuous"
    return "handoff"


def _as_utc(value: datetime) -> str:
    """Serialize a datetime as canonical UTC RFC 3339 text."""

    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _actor_key(role: Mapping[str, Any]) -> str:
    """Return a stable key for one observed R&R actor."""

    catalog_fields = (
        ("person", role.get("cataloged_person_id")),
        ("team", role.get("cataloged_team_id")),
        ("organization", role.get("cataloged_corporate_entity_id")),
    )
    for prefix, value in catalog_fields:
        if value:
            return f"{prefix}:{value}"
    parts = (
        str(role.get("actor_type_code") or "unknown"),
        str(role.get("actor_name") or ""),
        str(role.get("affiliated_organization_name") or ""),
    )
    return "text:" + "\u001f".join(normalize("NFKC", part).strip().lower() for part in parts)


def _score(value: object) -> float:
    """Return a finite JSON-compatible lineage score."""

    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("lineage score must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("lineage score must be finite")
    return result


def _prior_paths(
    ordered_event_ids: Sequence[str],
    edge_rows: Sequence[Mapping[str, Any]],
    *,
    maximum_depth: int,
    maximum_paths_per_event: int,
) -> dict[str, list[dict[str, Any]]]:
    """Return one deterministic shortest visible path per prior event."""

    event_index = {event_id: index for index, event_id in enumerate(ordered_event_ids)}
    reverse_edges: dict[str, list[dict[str, Any]]] = {event_id: [] for event_id in ordered_event_ids}
    for row in edge_rows:
        parent = str(row["parent_post_id"])
        child = str(row["child_post_id"])
        if parent not in event_index or child not in event_index:
            continue
        if event_index[parent] >= event_index[child]:
            continue
        reverse_edges[child].append(
            {
                "parent_event_id": parent,
                "child_event_id": child,
                "fused_score": _score(row["fused_score"]),
            }
        )
    for edges in reverse_edges.values():
        edges.sort(key=lambda edge: (event_index[edge["parent_event_id"]], edge["parent_event_id"]))

    result: dict[str, list[dict[str, Any]]] = {}
    for target in ordered_event_ids:
        queue: deque[tuple[str, tuple[str, ...], tuple[dict[str, Any], ...]]] = deque(
            [(target, (target,), ())]
        )
        best_depth = {target: 0}
        paths: list[dict[str, Any]] = []
        while queue and len(paths) < maximum_paths_per_event:
            current, reverse_event_path, reverse_edge_path = queue.popleft()
            depth = len(reverse_edge_path)
            if depth >= maximum_depth:
                continue
            for edge in reverse_edges[current]:
                parent = edge["parent_event_id"]
                if parent in reverse_event_path:
                    continue
                next_depth = depth + 1
                if best_depth.get(parent, maximum_depth + 1) <= next_depth:
                    continue
                best_depth[parent] = next_depth
                next_events = reverse_event_path + (parent,)
                next_edges = reverse_edge_path + (edge,)
                ordered_events = list(reversed(next_events))
                ordered_edges = list(reversed(next_edges))
                paths.append(
                    {
                        "source_event_id": parent,
                        "target_event_id": target,
                        "event_ids": ordered_events,
                        "edges": ordered_edges,
                        "minimum_fused_score": min(item["fused_score"] for item in ordered_edges),
                        "truth_status_code": "inferred",
                        "source_relation_code": "post_lineage_edge",
                        "provenance": "post_lineage_edge.fused_score",
                    }
                )
                queue.append((parent, next_events, next_edges))
                if len(paths) >= maximum_paths_per_event:
                    break
        paths.sort(
            key=lambda path: (
                len(path["edges"]),
                event_index[path["source_event_id"]],
                tuple(path["event_ids"]),
            )
        )
        result[target] = paths
    return result


def build_project_history_projection(
    *,
    project_key: str,
    focus_event_id: str,
    event_rows: Sequence[Mapping[str, Any]],
    match_rows: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
    edge_rows: Sequence[Mapping[str, Any]],
    maximum_depth: int = PROJECT_HISTORY_MAX_DEPTH,
    maximum_paths_per_event: int = PROJECT_HISTORY_MAX_PATHS_PER_EVENT,
    truncated: bool = False,
) -> dict[str, Any]:
    """Build a deterministic project-history projection from visible evidence.

    Every input row must already be caller-authorized. The function does not
    query storage or infer missing project membership, people, dates, or edges.
    ``truncated`` records that the storage boundary returned a bounded slice;
    it does not imply that any hidden row was inspected or inferred.
    """

    if not 1 <= maximum_depth <= PROJECT_HISTORY_MAX_DEPTH:
        raise ValueError(f"maximum_depth must be between 1 and {PROJECT_HISTORY_MAX_DEPTH}")
    if not 1 <= maximum_paths_per_event <= PROJECT_HISTORY_MAX_PATHS_PER_EVENT:
        raise ValueError(
            "maximum_paths_per_event must be between 1 and "
            f"{PROJECT_HISTORY_MAX_PATHS_PER_EVENT}"
        )
    normalized_key = normalize_project_key(project_key)
    unique_events: dict[str, Mapping[str, Any]] = {}
    for row in event_rows:
        post_id = str(row["post_id"])
        unique_events.setdefault(post_id, row)
    if focus_event_id not in unique_events:
        raise ValueError("focus event must be visible in the project history")
    ordered_events = sorted(
        unique_events.values(),
        key=lambda row: (row["created_at"], str(row["post_id"])),
    )
    event_ids = [str(row["post_id"]) for row in ordered_events]

    matches_by_post: dict[str, list[dict[str, Any]]] = {event_id: [] for event_id in event_ids}
    seen_matches: set[tuple[str, str, str]] = set()
    for row in match_rows:
        post_id = str(row["post_id"])
        if post_id not in matches_by_post:
            continue
        match_kind = str(row["match_kind_code"])
        matched_value = str(row["matched_value"])
        if normalize_project_key(matched_value) != normalized_key:
            continue
        dedupe_key = (post_id, match_kind, matched_value)
        if dedupe_key in seen_matches:
            continue
        seen_matches.add(dedupe_key)
        matches_by_post[post_id].append(
            {
                "match_kind_code": match_kind,
                "matched_value": matched_value,
                "truth_status_code": (
                    "observed" if match_kind.startswith("source_") else "inferred"
                ),
                "confidence": row.get("confidence"),
                "ontology_iri": row.get("ontology_iri"),
                "provenance": row.get("provenance"),
            }
        )

    roles_by_post: dict[str, list[dict[str, Any]]] = {event_id: [] for event_id in event_ids}
    for row in role_rows:
        post_id = str(row["post_id"])
        if post_id not in roles_by_post:
            continue
        roles_by_post[post_id].append(
            {
                "actor_key": _actor_key(row),
                "actor_name": row.get("actor_name"),
                "responsibility": row.get("responsibility"),
                "actor_type_code": row.get("actor_type_code"),
                "affiliated_organization_name": row.get("affiliated_organization_name"),
                "truth_status_code": "observed",
                "provenance": "post_summary_role",
            }
        )
    for roles in roles_by_post.values():
        roles.sort(key=lambda role: (role["actor_key"], str(role.get("responsibility") or "")))

    paths_by_post = _prior_paths(
        event_ids,
        edge_rows,
        maximum_depth=maximum_depth,
        maximum_paths_per_event=maximum_paths_per_event,
    )
    projected_events: list[dict[str, Any]] = []
    previous_actor_keys: list[str] | None = None
    for row in ordered_events:
        event_id = str(row["post_id"])
        actor_keys = [role["actor_key"] for role in roles_by_post[event_id]]
        transition = (
            None
            if previous_actor_keys is None
            else responsibility_transition_code(previous_actor_keys, actor_keys)
        )
        projected_events.append(
            {
                "event_id": event_id,
                "source_post_id": event_id,
                "event_title": str(row["post_title"]),
                "occurred_at": _as_utc(row["created_at"]),
                "event_type_code": classify_project_event(
                    title=str(row["post_title"]),
                    source_stage_code=row.get("source_stage_code"),
                    source_detail_state_code=row.get("source_detail_state_code"),
                    voc_type_code=row.get("voc_type_code"),
                    is_focus=event_id == focus_event_id,
                ),
                "event_type_basis_code": "display_classification",
                "time_basis_code": PROJECT_HISTORY_TIME_BASIS,
                "voc_type_code": row.get("voc_type_code"),
                "source_stage_code": row.get("source_stage_code"),
                "source_detail_state_code": row.get("source_detail_state_code"),
                "project_matches": sorted(
                    matches_by_post[event_id],
                    key=lambda item: (
                        item["match_kind_code"],
                        item["matched_value"],
                    ),
                ),
                "observed_responsibilities": roles_by_post[event_id],
                "responsibility_transition_code": transition,
                "related_prior_paths": paths_by_post[event_id],
            }
        )
        previous_actor_keys = actor_keys

    distinct_actor_keys = {
        role["actor_key"]
        for roles in roles_by_post.values()
        for role in roles
        if role["actor_key"]
    }
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "project_key": project_key.strip(),
        "normalized_project_key": normalized_key,
        "project_name": project_key.strip(),
        "focus_event_id": focus_event_id,
        "time_basis_code": PROJECT_HISTORY_TIME_BASIS,
        "event_count": len(projected_events),
        "distinct_observed_actor_count": len(distinct_actor_keys),
        "truncated": truncated,
        "events": projected_events,
    }

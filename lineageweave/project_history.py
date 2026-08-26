"""Build evidence-bound project histories from already-authorized rows.

Callers must apply RBAC, ABAC, source eligibility, and knowledge-cutoff
filtering before invoking this module. The pure projection layer then orders
visible source records, preserves explicit and semantic project evidence,
compares observed responsibility evidence, and exposes persisted lineage as
related history without promoting it to causality or an HR assignment ledger.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
import math
from typing import Any
from unicodedata import normalize

PROJECT_HISTORY_CONTRACT_VERSION = 1
PROJECT_HISTORY_TIME_BASIS = "source_post_created_at_fallback"
PROJECT_HISTORY_DOCUMENT_TIME_BASIS = "document_time"
PROJECT_HISTORY_MAX_DEPTH = 8
PROJECT_HISTORY_MAX_PATHS_PER_EVENT = 32

_VOC_CODES = frozenset({"voc", "vocc", "voco", "vom", "vop"})
_TRUTH_ORDER = {"observed": 0, "inferred": 1}
_DISPLAY_NAME_ORDER = {"source_project_name": 0, "semantic_project_name": 1}


def normalize_project_key(value: str) -> str:
    """Return the exact project-identity comparison key.

    Unicode compatibility normalization lets full-width and compatibility
    forms match without introducing fuzzy identity. Empty and oversized keys
    fail closed.
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
    """Return a non-authoritative display classification for one source row.

    Only the persisted controlled VOC code is classified. Free-text titles,
    stages, and detail states remain evidence fields; this projection never
    guesses lifecycle semantics from words. ``is_focus`` is retained for
    contract compatibility but never changes the truth status or creates an
    event.
    """

    del is_focus
    del title, source_stage_code, source_detail_state_code
    if (voc_type_code or "").strip().lower() in _VOC_CODES:
        return "voc_received"
    return "source_recorded"


def responsibility_transition_code(
    previous_actor_keys: Sequence[str], current_actor_keys: Sequence[str]
) -> str:
    """Compare adjacent observed responsibility evidence.

    Missing evidence on either row is an ``assignment_gap`` evidence state,
    not proof of an operational or HR vacancy. Equal non-empty actor sets are
    continuous; different non-empty sets are a handoff.
    """

    previous = frozenset(key for key in previous_actor_keys if key)
    current = frozenset(key for key in current_actor_keys if key)
    if not previous or not current:
        return "assignment_gap"
    if previous == current:
        return "continuous"
    return "handoff"


def _as_utc(value: datetime) -> str:
    """Serialize a source clock as canonical UTC RFC 3339 text."""

    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _actor_key(role: Mapping[str, Any]) -> str:
    """Return a stable key for one observed role actor."""

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
    if math.isnan(result) or result in (float("inf"), float("-inf")):
        raise ValueError("lineage score must be finite")
    return result


def _prior_paths(
    ordered_event_ids: Sequence[str],
    edge_rows: Sequence[Mapping[str, Any]],
    *,
    maximum_depth: int,
    maximum_paths_per_event: int,
) -> dict[str, list[dict[str, Any]]]:
    """Return deterministic shortest visible predecessor paths per event."""

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
    focus_event_id: str | None,
    event_rows: Sequence[Mapping[str, Any]],
    match_rows: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
    edge_rows: Sequence[Mapping[str, Any]],
    truncated: bool = False,
    maximum_depth: int = PROJECT_HISTORY_MAX_DEPTH,
    maximum_paths_per_event: int = PROJECT_HISTORY_MAX_PATHS_PER_EVENT,
) -> dict[str, Any]:
    """Build the versioned project-history projection.

    Inputs must already be visible, eligible, and within the requested cutoff.
    Duplicate source rows and role rows are collapsed deterministically. An
    observed source project name outranks an inferred semantic display name.
    """

    normalized_key = normalize_project_key(project_key)
    if maximum_depth < 1 or maximum_depth > PROJECT_HISTORY_MAX_DEPTH:
        raise ValueError("maximum_depth is outside the supported bound")
    if maximum_paths_per_event < 1 or maximum_paths_per_event > PROJECT_HISTORY_MAX_PATHS_PER_EVENT:
        raise ValueError("maximum_paths_per_event is outside the supported bound")

    deduplicated: dict[str, Mapping[str, Any]] = {}
    for row in event_rows:
        event_id = str(row["post_id"])
        current = deduplicated.get(event_id)
        row_clock = row.get("event_occurred_at") or row["created_at"]
        current_clock = (
            current.get("event_occurred_at") or current["created_at"]
            if current is not None
            else None
        )
        if current is None or (row_clock, row["created_at"], event_id) < (
            current_clock,
            current["created_at"],
            event_id,
        ):
            deduplicated[event_id] = row
    ordered_rows = sorted(
        deduplicated.values(),
        key=lambda row: (
            row.get("event_occurred_at") or row["created_at"],
            row["created_at"],
            str(row["post_id"]),
        ),
    )
    if not ordered_rows:
        raise ValueError("project history requires at least one visible event")
    ordered_ids = [str(row["post_id"]) for row in ordered_rows]
    event_index = {event_id: index for index, event_id in enumerate(ordered_ids)}
    effective_focus = focus_event_id or ordered_ids[-1]
    if effective_focus not in event_index:
        raise ValueError("focus event is not in the visible project history")

    matches_by_event: dict[str, list[dict[str, Any]]] = {event_id: [] for event_id in ordered_ids}
    display_names: list[tuple[int, int, str, str]] = []
    seen_matches: set[tuple[str, str, str]] = set()
    for row in match_rows:
        event_id = str(row["post_id"])
        if event_id not in matches_by_event:
            continue
        matched_value = str(row["matched_value"])
        if normalize_project_key(matched_value) != normalized_key:
            continue
        kind = str(row["match_kind_code"])
        key = (event_id, kind, matched_value)
        if key in seen_matches:
            continue
        seen_matches.add(key)
        confidence = row.get("confidence")
        if confidence is not None:
            confidence = _score(confidence)
        truth = "observed" if kind.startswith("source_") else "inferred"
        matches_by_event[event_id].append(
            {
                "match_kind_code": kind,
                "matched_value": matched_value,
                "truth_status_code": truth,
                "confidence": confidence,
                "ontology_iri": row.get("ontology_iri"),
                "provenance": str(row["provenance"]),
            }
        )
        if kind in _DISPLAY_NAME_ORDER:
            display_names.append(
                (
                    _DISPLAY_NAME_ORDER[kind],
                    event_index[event_id],
                    normalize_project_key(matched_value),
                    matched_value,
                )
            )
    for matches in matches_by_event.values():
        matches.sort(
            key=lambda item: (
                _TRUTH_ORDER[item["truth_status_code"]],
                item["match_kind_code"],
                item["matched_value"],
            )
        )

    roles_by_event: dict[str, list[dict[str, Any]]] = {event_id: [] for event_id in ordered_ids}
    actor_keys_by_event: dict[str, list[str]] = {event_id: [] for event_id in ordered_ids}
    distinct_actor_keys: set[str] = set()
    seen_roles: set[tuple[str, str, str]] = set()
    for row in role_rows:
        event_id = str(row["post_id"])
        if event_id not in roles_by_event:
            continue
        actor_key = _actor_key(row)
        responsibility = str(row["responsibility"])
        role_key = (event_id, actor_key, responsibility)
        if role_key in seen_roles:
            continue
        seen_roles.add(role_key)
        distinct_actor_keys.add(actor_key)
        actor_keys_by_event[event_id].append(actor_key)
        roles_by_event[event_id].append(
            {
                "actor_key": actor_key,
                "actor_name": str(row["actor_name"]),
                "actor_type_code": str(row["actor_type_code"]),
                "affiliated_organization_name": row.get("affiliated_organization_name"),
                "responsibility": responsibility,
                "truth_status_code": "observed",
                "provenance": "post_summary_role",
            }
        )
    for event_id, roles in roles_by_event.items():
        roles.sort(key=lambda role: (role["actor_type_code"], role["actor_name"], role["actor_key"]))
        actor_keys_by_event[event_id] = sorted(set(actor_keys_by_event[event_id]))

    paths_by_event = _prior_paths(
        ordered_ids,
        edge_rows,
        maximum_depth=maximum_depth,
        maximum_paths_per_event=maximum_paths_per_event,
    )

    events: list[dict[str, Any]] = []
    previous_actor_keys: Sequence[str] | None = None
    for row in ordered_rows:
        event_id = str(row["post_id"])
        event_occurred_at = row.get("event_occurred_at")
        time_basis_code = (
            PROJECT_HISTORY_DOCUMENT_TIME_BASIS
            if event_occurred_at is not None
            else PROJECT_HISTORY_TIME_BASIS
        )
        current_actor_keys = actor_keys_by_event[event_id]
        transition = (
            None
            if previous_actor_keys is None
            else responsibility_transition_code(previous_actor_keys, current_actor_keys)
        )
        events.append(
            {
                "event_id": event_id,
                "source_post_id": event_id,
                "event_title": str(row["post_title"]),
                "event_type_code": classify_project_event(
                    title=str(row["post_title"]),
                    source_stage_code=row.get("source_stage_code"),
                    source_detail_state_code=row.get("source_detail_state_code"),
                    voc_type_code=row.get("voc_type_code"),
                    is_focus=event_id == effective_focus,
                ),
                "event_type_basis_code": "controlled_source_code",
                "occurred_at": _as_utc(event_occurred_at or row["created_at"]),
                "time_basis_code": time_basis_code,
                "voc_type_code": row.get("voc_type_code"),
                "source_stage_code": row.get("source_stage_code"),
                "source_detail_state_code": row.get("source_detail_state_code"),
                "project_matches": matches_by_event[event_id],
                "observed_responsibilities": roles_by_event[event_id],
                "responsibility_transition_code": transition,
                "related_prior_paths": paths_by_event[event_id],
            }
        )
        previous_actor_keys = current_actor_keys

    project_name = min(display_names)[3] if display_names else project_key.strip()
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "project_key": project_key.strip(),
        "normalized_project_key": normalized_key,
        "project_name": project_name,
        "focus_event_id": effective_focus,
        "time_basis_code": (
            PROJECT_HISTORY_DOCUMENT_TIME_BASIS
            if all(event["time_basis_code"] == PROJECT_HISTORY_DOCUMENT_TIME_BASIS for event in events)
            else PROJECT_HISTORY_TIME_BASIS
        ),
        "event_count": len(events),
        "distinct_observed_actor_count": len(distinct_actor_keys),
        "truncated": bool(truncated),
        "events": events,
    }

"""Load source posts, reconstruct lineage, and persist auditable evidence.

This module is the only live-database writer for selected Event Lineage edges,
their versioned reconstruction run, normalized active weight profile, and
per-edge channel score/contribution rows. Missing channels stay absent, and
Buyer reads reapply endpoint ABAC before returning any evidence.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.lineage_persistence import lineage_reconstruction_spec
from lineageweave.models import Edge, Record

_LINEAGE_CHANNEL_LOOKUP_CODE_BY_NAME = {
    "temporal": "lineage_channel_temporal",
    "secondary_key": "lineage_channel_secondary_key",
    "text": "lineage_channel_text",
    "llm": "lineage_channel_llm",
}
_LINEAGE_CHANNEL_NAME_BY_LOOKUP_CODE = {
    lookup_code: channel_name
    for channel_name, lookup_code in _LINEAGE_CHANNEL_LOOKUP_CODE_BY_NAME.items()
}
_FUSION_TOLERANCE = 1e-9


def _occurred_at(value: datetime) -> datetime:
    """Return the naive UTC-style timestamp expected by reconstruction."""

    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def reconstruct_group_key(row: Mapping[str, Any]) -> str:
    """Use the same group key for reconstruction and Buyer DAG display."""

    stored_group = (row.get("thread_group_key") or "").strip()
    return stored_group or str(row["process_unit_id"] or row["corporate_entity_id"])


def records_from_source_posts(rows: list[Mapping[str, Any]]) -> list[Record]:
    """Map persisted posts to immutable reconstruction records."""

    records: list[Record] = []
    for row in rows:
        records.append(
            Record(
                str(row["post_id"]),
                reconstruct_group_key(row),
                row["post_title"],
                _occurred_at(row["created_at"]),
                row.get("secondary_grouping_key") or "",
            )
        )
    return records


def _validated_channel_profile(
    channel_weights: Mapping[str, float],
) -> tuple[tuple[str, str, float], ...]:
    """Validate and order the normalized active fusion profile."""

    unknown = set(channel_weights) - set(_LINEAGE_CHANNEL_LOOKUP_CODE_BY_NAME)
    if unknown:
        raise ValueError(f"unsupported lineage channel: {sorted(unknown)[0]}")
    rows: list[tuple[str, str, float]] = []
    for channel_name, lookup_code in _LINEAGE_CHANNEL_LOOKUP_CODE_BY_NAME.items():
        if channel_name not in channel_weights:
            continue
        weight = float(channel_weights[channel_name])
        if not math.isfinite(weight) or not 0.0 < weight <= 1.0:
            raise ValueError(
                f"lineage channel weight must be between 0 and 1: "
                f"{channel_name}={weight}"
            )
        rows.append((channel_name, lookup_code, weight))
    total = sum(weight for _, _, weight in rows)
    if not rows or not math.isclose(total, 1.0, abs_tol=_FUSION_TOLERANCE):
        raise ValueError("active lineage channel weights must sum to 1")
    return tuple(rows)


def _validated_channel_rows(
    edge: Edge,
    profile: tuple[tuple[str, str, float], ...],
) -> tuple[tuple[str, float, float], ...]:
    """Return score and contribution rows that reconcile to one fused edge."""

    profile_names = {channel_name for channel_name, _, _ in profile}
    if set(edge.channel_scores) != profile_names:
        raise ValueError("edge active channel set does not match reconstruction profile")
    rows: list[tuple[str, float, float]] = []
    for channel_name, lookup_code, weight in profile:
        score = float(edge.channel_scores[channel_name])
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError(
                f"lineage channel score must be between 0 and 1: "
                f"{channel_name}={score}"
            )
        rows.append((lookup_code, score, score * weight))
    fused_score = float(edge.fused_score)
    contribution_total = sum(contribution for _, _, contribution in rows)
    if not math.isfinite(fused_score) or not math.isclose(
        contribution_total,
        fused_score,
        abs_tol=_FUSION_TOLERANCE,
    ):
        raise ValueError(
            "lineage channel contributions do not reconcile to fused score"
        )
    return tuple(rows)


def _public_channel_name(lookup_code: str) -> str:
    """Translate a database lookup code to the stable Buyer API key."""

    channel_name = _LINEAGE_CHANNEL_NAME_BY_LOOKUP_CODE.get(lookup_code)
    if channel_name is None:
        raise ValueError(f"unsupported persisted lineage channel: {lookup_code}")
    return channel_name


async def persist_lineage_edges(
    conn: asyncpg.Connection,
    edges: list[Edge],
    *,
    channel_weights: Mapping[str, float],
    reconstruction_version: str,
) -> None:
    """Atomically replace edges and their complete versioned audit evidence.

    Validation finishes before the first database statement. The caller owns
    the surrounding transaction so the run, profile, parent edges, and channel
    children either commit together or all roll back. Superseded run profiles
    are removed after their cascading edge evidence has been replaced.
    """

    version = reconstruction_version.strip()
    if not version:
        raise ValueError("reconstruction_version must not be empty")
    profile = _validated_channel_profile(channel_weights)
    validated_edges = [
        (edge, _validated_channel_rows(edge, profile)) for edge in edges
    ]

    if not validated_edges:
        await conn.execute("delete from post_lineage_edge")
        await conn.execute(
            "delete from lineage_reconstruction_run old_run "
            "where not exists ("
            "select 1 from post_lineage_edge edge "
            "where edge.lineage_reconstruction_run_id = "
            "old_run.lineage_reconstruction_run_id)"
        )
        return

    reconstruction_run_id = uuid4()
    generated_at = datetime.now(timezone.utc)
    await conn.execute(
        "insert into lineage_reconstruction_run "
        "(lineage_reconstruction_run_id, reconstruction_version, generated_at) "
        "values ($1, $2, $3)",
        reconstruction_run_id,
        version,
        generated_at,
    )
    for _, channel_code, channel_weight in profile:
        await conn.execute(
            "insert into lineage_reconstruction_run_channel "
            "(lineage_reconstruction_run_id, channel_code, channel_weight) "
            "values ($1, $2, $3)",
            reconstruction_run_id,
            channel_code,
            channel_weight,
        )

    await conn.execute("delete from post_lineage_edge")
    for edge, channel_rows in validated_edges:
        await conn.execute(
            "insert into post_lineage_edge "
            "(parent_post_id, child_post_id, fused_score, "
            "lineage_reconstruction_run_id) "
            "values ($1::uuid, $2::uuid, $3, $4)",
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
            reconstruction_run_id,
        )
        for channel_code, channel_score, channel_contribution in channel_rows:
            await conn.execute(
                "insert into lineage_edge_channel_score "
                "(parent_post_id, child_post_id, channel_code, channel_score, "
                "channel_contribution) values ($1::uuid, $2::uuid, $3, $4, $5)",
                edge.parent_id,
                edge.child_id,
                channel_code,
                channel_score,
                channel_contribution,
            )

    await conn.execute(
        "delete from lineage_reconstruction_run old_run "
        "where old_run.lineage_reconstruction_run_id <> $1 "
        "and not exists ("
        "select 1 from post_lineage_edge edge "
        "where edge.lineage_reconstruction_run_id = "
        "old_run.lineage_reconstruction_run_id)",
        reconstruction_run_id,
    )


async def rebuild_lineage(conn: asyncpg.Connection) -> list[Edge]:
    """Reconstruct every eligible post and replace the persisted evidence."""

    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    spec = lineage_reconstruction_spec(records_from_source_posts(rows))
    await persist_lineage_edges(
        conn,
        list(spec.edges),
        channel_weights=spec.channel_weights,
        reconstruction_version=spec.reconstruction_version,
    )
    return list(spec.edges)


def _ranked_channel_evidence(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Order one edge's evidence by contribution, then controlled signal order."""

    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row["contribution"]),
            int(row["display_order"]),
            str(row["signal_code"]),
        ),
    )
    return [
        {
            "signal_code": row["signal_code"],
            "signal_label": row["signal_label"],
            "score": row["score"],
            "weight": row["weight"],
            "contribution": row["contribution"],
            "rank": rank,
        }
        for rank, row in enumerate(ordered, start=1)
    ]


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = 500,
    focus_post_id: str | None = None,
) -> dict[str, Any]:
    """Return an ABAC-filtered Buyer graph with exact edge evidence.

    ``focus_post_id`` returns its complete visible connected component. The
    landing view remains bounded to the newest ``limit`` visible nodes.
    Reconstruction scores are inferred, non-causal evidence and never grant
    access to an endpoint post.
    """

    posts = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, process_unit_id, thread_group_key, created_at "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    visible_all = [row for row in posts if can_see_post(row)]
    edge_rows = await conn.fetch(
        "select parent_post_id, child_post_id, fused_score, "
        "lineage_reconstruction_run_id from post_lineage_edge"
    )

    if focus_post_id is None:
        visible = sorted(
            visible_all,
            key=lambda row: (row["created_at"], str(row["post_id"])),
            reverse=True,
        )[:limit]
        truncated = len(visible_all) > len(visible)
    else:
        focus_id = str(focus_post_id)
        focus_visible = any(str(row["post_id"]) == focus_id for row in visible_all)
        neighbors: dict[str, set[str]] = {}
        for edge in edge_rows:
            parent_id = str(edge["parent_post_id"])
            child_id = str(edge["child_post_id"])
            neighbors.setdefault(parent_id, set()).add(child_id)
            neighbors.setdefault(child_id, set()).add(parent_id)

        component_ids: set[str] = set()
        frontier = [focus_id] if focus_visible else []
        while frontier:
            current_id = frontier.pop()
            if current_id in component_ids:
                continue
            component_ids.add(current_id)
            frontier.extend(neighbors.get(current_id, set()) - component_ids)

        if len(component_ids) <= 1:
            visible = []
        else:
            visible = [
                row for row in visible_all if str(row["post_id"]) in component_ids
            ]
        truncated = False

    visible_ids = {str(row["post_id"]) for row in visible}
    visible_edges = [
        row
        for row in edge_rows
        if str(row["parent_post_id"]) in visible_ids
        and str(row["child_post_id"]) in visible_ids
    ]

    channel_rows = []
    if visible_edges:
        channel_rows = await conn.fetch(
            "select score.parent_post_id, score.child_post_id, "
            "score.channel_code, lookup.lookup_label as channel_label, "
            "score.channel_score, profile.channel_weight, "
            "score.channel_contribution, lookup.display_order, "
            "run.reconstruction_version, run.generated_at "
            "from lineage_edge_channel_score score "
            "join post_lineage_edge edge "
            "on edge.parent_post_id = score.parent_post_id "
            "and edge.child_post_id = score.child_post_id "
            "join lineage_reconstruction_run run "
            "on run.lineage_reconstruction_run_id = "
            "edge.lineage_reconstruction_run_id "
            "join lineage_reconstruction_run_channel profile "
            "on profile.lineage_reconstruction_run_id = "
            "run.lineage_reconstruction_run_id "
            "and profile.channel_code = score.channel_code "
            "join common_lookup_value lookup "
            "on lookup.lookup_code = score.channel_code "
            "where score.parent_post_id = any($1::uuid[]) "
            "and score.child_post_id = any($1::uuid[]) "
            "order by score.parent_post_id, score.child_post_id, "
            "score.channel_contribution desc, lookup.display_order, "
            "score.channel_code",
            sorted(visible_ids),
        )

    channel_scores_by_edge: dict[tuple[str, str], dict[str, float]] = {}
    raw_evidence_by_edge: dict[tuple[str, str], list[dict[str, Any]]] = {}
    reconstruction_by_edge: dict[tuple[str, str], tuple[str, str]] = {}
    for row in channel_rows:
        parent_id = str(row["parent_post_id"])
        child_id = str(row["child_post_id"])
        if parent_id not in visible_ids or child_id not in visible_ids:
            continue
        channel_name = _public_channel_name(str(row["channel_code"]))
        channel_score = float(row["channel_score"])
        channel_weight = float(row["channel_weight"])
        channel_contribution = float(row["channel_contribution"])
        if not 0.0 <= channel_score <= 1.0:
            raise ValueError("persisted lineage channel score must be between 0 and 1")
        if not 0.0 < channel_weight <= 1.0:
            raise ValueError("persisted lineage channel weight must be between 0 and 1")
        if not math.isclose(
            channel_score * channel_weight,
            channel_contribution,
            abs_tol=_FUSION_TOLERANCE,
        ):
            raise ValueError("persisted lineage channel contribution is inconsistent")
        edge_key = (parent_id, child_id)
        channel_scores_by_edge.setdefault(edge_key, {})[channel_name] = channel_score
        raw_evidence_by_edge.setdefault(edge_key, []).append(
            {
                "signal_code": channel_name,
                "signal_label": str(row["channel_label"]),
                "score": channel_score,
                "weight": channel_weight,
                "contribution": channel_contribution,
                "display_order": int(row["display_order"]),
            }
        )
        reconstruction = (
            str(row["reconstruction_version"]),
            row["generated_at"].isoformat(),
        )
        previous = reconstruction_by_edge.setdefault(edge_key, reconstruction)
        if previous != reconstruction:
            raise ValueError("persisted lineage reconstruction metadata is inconsistent")

    children_of: dict[str, list[str]] = {}
    for row in visible_edges:
        children_of.setdefault(str(row["parent_post_id"]), []).append(
            str(row["child_post_id"])
        )
    child_ids = {str(row["child_post_id"]) for row in visible_edges}
    nodes = []
    for row in visible:
        post_id = str(row["post_id"])
        nodes.append(
            {
                "id": post_id,
                "group": reconstruct_group_key(row),
                "label": row["post_title"],
                "occurred_at": row["created_at"].isoformat(),
                "is_root": post_id not in child_ids,
                "is_branch_point": len(children_of.get(post_id, [])) >= 2,
            }
        )

    edges = []
    for row in visible_edges:
        edge_key = (str(row["parent_post_id"]), str(row["child_post_id"]))
        evidence = _ranked_channel_evidence(raw_evidence_by_edge.get(edge_key, []))
        fused_score = float(row["fused_score"])
        run_id = row.get("lineage_reconstruction_run_id")
        if run_id is not None and not evidence:
            raise ValueError("persisted lineage run is missing channel evidence")
        if run_id is None and evidence:
            raise ValueError("lineage channel evidence has no reconstruction run")
        if evidence:
            if not math.isclose(
                sum(item["weight"] for item in evidence),
                1.0,
                abs_tol=_FUSION_TOLERANCE,
            ):
                raise ValueError("persisted lineage channel weights do not sum to 1")
            if not math.isclose(
                sum(item["contribution"] for item in evidence),
                fused_score,
                abs_tol=_FUSION_TOLERANCE,
            ):
                raise ValueError(
                    "persisted lineage evidence does not reconcile to fused score"
                )
        reconstruction = reconstruction_by_edge.get(edge_key)
        edges.append(
            {
                "source": edge_key[0],
                "target": edge_key[1],
                "fused_score": fused_score,
                "channel_scores": channel_scores_by_edge.get(edge_key, {}),
                "channel_evidence": evidence,
                "reconstruction_version": reconstruction[0] if reconstruction else None,
                "reconstructed_at": reconstruction[1] if reconstruction else None,
            }
        )
    return {"nodes": nodes, "edges": edges, "truncated": truncated}

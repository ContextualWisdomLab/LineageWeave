"""Load ``source_post`` rows, run ``reconstruct``, persist ``post_lineage_edge``.

This is the product half of ``lineageweave.lineage_persistence``: the
library flattens trees; this module is the only writer of
``post_lineage_edge`` from a live database. Reconstruct grouping is
read from ``thread_group_key`` / ``secondary_grouping_key`` -- the
same keys ``reconstruct()`` was given when the posts were ingested --
not derived from process unit or voc type.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.interval_relation import (
    INTERVAL_RELATION_LABELS,
    allen_interval_relation,
    interval_from_post,
    interval_relation_from_current,
)
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge, Record

# ADR 0145 rejected the unanchored estimator. A future accepted ADR must add
# its independently validated method code here before persisted weights can run.
_SUPPORTED_ANCHOR_METHOD_CODES: frozenset[str] = frozenset()


def _occurred_at(value: datetime) -> datetime:
    """Reconstruct expects naive datetimes; asyncpg returns timestamptz."""
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def reconstruct_group_key(row: Mapping[str, Any]) -> str:
    """Same grouping rebuild uses: persisted thread key, else PU, else corp.

    Display ``group`` on ``GET /api/lineage`` must use this exact fallback
    so the DAG cannot split a thread reconstruct would keep together.
    """
    stored_group = (row.get("thread_group_key") or "").strip()
    return stored_group or str(row["process_unit_id"] or row["corporate_entity_id"])


def records_from_source_posts(rows: list[Mapping[str, Any]]) -> list[Record]:
    """Map ``source_post`` rows onto reconstruct ``Record``s.

    ``group_key`` and ``secondary_key`` come from the persisted
    ``thread_group_key`` / ``secondary_grouping_key`` columns. Deriving
    them from process unit or voc type collapses independent threads
    (A-100 vs B-200, proj-alpha vs empty) and loses the designed fork.
    Posts ingested without those keys (empty string) fall back to
    process unit, then corporate entity, with an empty secondary key.
    """
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


def interval_relation_code_for_edge(
    parent_row: Mapping[str, Any], child_row: Mapping[str, Any]
) -> str:
    """Allen relation of the parent creation-day point toward the child."""
    return allen_interval_relation(
        interval_from_post(parent_row["created_at"]),
        interval_from_post(child_row["created_at"]),
    )


async def persist_lineage_edges(
    conn: asyncpg.Connection,
    edges: list[Edge],
    points_by_post_id: Mapping[str, Mapping[str, Any]],
) -> None:
    """Replace ``post_lineage_edge`` with ``edges`` (reconstruct is source of truth)."""
    missing_point_ids = {
        post_id
        for edge in edges
        for post_id in (edge.parent_id, edge.child_id)
        if post_id not in points_by_post_id
    }
    if missing_point_ids:
        raise ValueError(
            "missing observed interval point for post ids: "
            + ", ".join(sorted(missing_point_ids))
        )
    await conn.execute("delete from post_lineage_edge")
    for edge in edges:
        relation_code = interval_relation_code_for_edge(
            points_by_post_id[edge.parent_id], points_by_post_id[edge.child_id]
        )
        await conn.execute(
            "insert into post_lineage_edge "
            "(parent_post_id, child_post_id, fused_score, interval_relation_code) "
            "values ($1::uuid, $2::uuid, $3, $4)",
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
            relation_code,
        )


async def load_estimated_channel_weights(
    conn: asyncpg.Connection, active_channels: set[str]
) -> dict[str, float] | None:
    """Load only a complete vector from an independently anchored method.

    ADR 0145 currently authorizes no anchor method. A partial or invalid vector
    returns ``None`` rather than being repaired. A database that has not applied
    migration 0135 is likewise an unavailable state, detected without issuing a
    statement that would abort the caller's outer PostgreSQL transaction.
    """
    table_exists = await conn.fetchval(
        "select to_regclass('public.lineage_channel_weight') is not null"
    )
    if not table_exists:
        return None
    rows = await conn.fetch(
        "select channel_code, weight_value, estimation_run_id, "
        "estimation_method_code, estimator_version, anchor_method_code, "
        "source_snapshot_sha256, sample_pair_count, knowledge_cutoff "
        "from lineage_channel_weight"
    )
    persisted = {row["channel_code"]: float(row["weight_value"]) for row in rows}
    if not persisted or set(persisted) != active_channels:
        return None
    if any(
        not math.isfinite(weight) or weight <= 0 or weight > 1
        for weight in persisted.values()
    ):
        return None
    if not math.isclose(sum(persisted.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        return None
    provenance = {
        (
            row["estimation_run_id"],
            row["estimation_method_code"],
            row["estimator_version"],
            row["anchor_method_code"],
            row["source_snapshot_sha256"],
            row["sample_pair_count"],
            row["knowledge_cutoff"],
        )
        for row in rows
    }
    if len(provenance) != 1:
        return None
    run = next(iter(provenance))
    (
        run_id,
        estimation_method,
        estimator_version,
        anchor_method,
        snapshot_digest,
        sample_pair_count,
        knowledge_cutoff,
    ) = run
    if (
        run_id is None
        or not isinstance(estimation_method, str)
        or not estimation_method.strip()
        or not isinstance(estimator_version, str)
        or not estimator_version.strip()
        or not isinstance(anchor_method, str)
        or anchor_method not in _SUPPORTED_ANCHOR_METHOD_CODES
        or not isinstance(snapshot_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", snapshot_digest) is None
        or not isinstance(sample_pair_count, int)
        or isinstance(sample_pair_count, bool)
        or sample_pair_count < 200
        or not isinstance(knowledge_cutoff, datetime)
    ):
        return None
    return persisted


async def rebuild_lineage(conn: asyncpg.Connection) -> list[Edge]:
    """Reconstruct lineage for every ``source_post`` and persist the edges."""
    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    # No adjudication client is wired on this path, so the active channel
    # set is the three deterministic channels (reconstruct drops llm when
    # unavailable rather than faking it).
    weights = await load_estimated_channel_weights(
        conn, {"temporal", "secondary_key", "text"}
    )
    edges = lineage_edge_specs(records_from_source_posts(rows), weights=weights)
    await persist_lineage_edges(conn, edges, {str(row["post_id"]): row for row in rows})
    return edges


def _interval_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    code = row.get("interval_relation_code")
    if not code:
        return {}
    label = row.get("interval_relation_label") or INTERVAL_RELATION_LABELS.get(str(code))
    payload = {"interval_relation_code": str(code)}
    if label:
        payload["interval_relation_label"] = str(label)
    return payload


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = 500,
    focus_post_id: str | None = None,
    include_isolated: bool = False,
) -> dict[str, Any]:
    """ABAC-filtered graph bounded for the browser's initial viewport.

    The persisted graph can contain tens of thousands of posts. The UI opens
    individual posts for complete lineage, while this landing projection keeps
    only the newest ``limit`` visible nodes and edges between them.
    """
    posts = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, process_unit_id, thread_group_key, created_at "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    visible_all = [row for row in posts if can_see_post(row)]
    edge_rows = await conn.fetch(
        "select parent_post_id, child_post_id, fused_score, "
        "interval_relation_code from post_lineage_edge"
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

        visible = (
            [row for row in visible_all if str(row["post_id"]) in component_ids]
            if include_isolated or len(component_ids) > 1
            else []
        )
        truncated = False

    visible_ids = {str(row["post_id"]) for row in visible}
    visible_edges = [
        row
        for row in edge_rows
        if str(row["parent_post_id"]) in visible_ids and str(row["child_post_id"]) in visible_ids
    ]
    children_of: dict[str, list[str]] = {}
    for row in visible_edges:
        children_of.setdefault(str(row["parent_post_id"]), []).append(str(row["child_post_id"]))
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
    edges = [
        {
            "source": str(row["parent_post_id"]),
            "target": str(row["child_post_id"]),
            "fused_score": float(row["fused_score"]),
            **_interval_payload(row),
        }
        for row in visible_edges
    ]
    return {"nodes": nodes, "edges": edges, "truncated": truncated}


async def interval_relations_for_post(
    conn: asyncpg.Connection, post_id: str
) -> dict[str, dict[str, Any]]:
    """Allen labels on direct reconstructed neighbors of ``post_id``."""
    rows = await conn.fetch(
        "select parent_post_id, child_post_id, interval_relation_code "
        "from post_lineage_edge "
        "where parent_post_id = $1::uuid or child_post_id = $1::uuid",
        post_id,
    )
    current = str(post_id)
    relations: dict[str, dict[str, Any]] = {}
    for row in rows:
        parent_id = str(row["parent_post_id"])
        child_id = str(row["child_post_id"])
        other_id = child_id if parent_id == current else parent_id
        current_is_parent = parent_id == current
        stored = _interval_payload(row)
        code = stored.get("interval_relation_code")
        if not code:
            continue
        oriented = interval_relation_from_current(str(code), current_is_parent)
        relations[other_id] = {
            "interval_relation_code": oriented,
            "interval_relation_label": INTERVAL_RELATION_LABELS.get(
                oriented, stored.get("interval_relation_label")
            ),
            "interval_is_parent": current_is_parent,
        }
    return relations


async def lineage_graphs_for_posts(
    conn: asyncpg.Connection,
    can_see_post,
    post_ids: list[str],
) -> dict[str, Any]:
    """Merge each post's full reconstructed thread into one ``LineageGraph``.

    An Ask Agent answer can cite several posts from unrelated reconstruct
    threads -- e.g. two separate customer complaints that happen to share a
    keyword. The frontend's ``LineageDag`` already renders one ``LineageGraph``
    as several independent git-branch-style figures, one per
    ``reconstruct_group_key`` (see ``lineageLayout.ts``'s ``layoutLineageDag``);
    merging every cited post's thread into a single graph is enough to get
    that multi-graph rendering for free, no new frontend layout needed.

    ponytail: one ``visible_lineage_graph`` call per post (each a bounded
    ``source_post`` + full ``post_lineage_edge`` scan) -- fine for the
    existing citation cap (``_POST_CHAT_SOURCE_LIMIT`` = 8), revisit with a
    single batched query if that cap grows materially.
    """
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    truncated = False
    for post_id in dict.fromkeys(post_ids):
        graph = await visible_lineage_graph(
            conn, can_see_post, focus_post_id=post_id, include_isolated=True
        )
        truncated = truncated or graph["truncated"]
        for node in graph["nodes"]:
            nodes_by_id[node["id"]] = node
        for edge in graph["edges"]:
            edges_by_key[(edge["source"], edge["target"])] = edge
    return {
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_key.values()),
        "truncated": truncated,
    }

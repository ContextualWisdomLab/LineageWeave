"""Load ``source_post`` rows, run ``reconstruct``, persist ``post_lineage_edge``.

This is the product half of ``lineageweave.lineage_persistence``: the
library flattens trees; this module is the only writer of
``post_lineage_edge`` from a live database. Reconstruct grouping is
read from ``thread_group_key`` / ``secondary_grouping_key`` -- the
same keys ``reconstruct()`` was given when the posts were ingested --
not derived from process unit or voc type.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Mapping

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.adjudication_client import AdjudicationClient
from lineageweave.lineage_persistence import (
    LOOKUP_CODE_TO_SIGNAL,
    lineage_edge_specs,
    lineage_rebuild_spec,
    rank_channel_evidence,
)
from lineageweave.models import Edge, Record


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


async def persist_lineage_edges(conn: asyncpg.Connection, edges: list[Edge]) -> None:
    """Replace live Event Lineage with ``edges`` and their channel evidence.

    Reconstruct is the source of truth. The delete is cascaded onto
    ``post_lineage_edge_signal`` so a rebuild cannot leave orphan or
    stale signal rows. Rebuild metadata is replaced in the same
    connection so version, weights, and generated-at stay aligned with
    the new graph.
    """
    spec = lineage_rebuild_spec(edges)
    await conn.execute("delete from post_lineage_edge")
    await conn.execute("delete from event_lineage_rebuild")
    await conn.execute(
        "insert into event_lineage_rebuild "
        "(rebuild_lock, reconstruction_version, generated_at, min_fused_score, candidate_window) "
        "values (true, $1, now(), $2, $3)",
        spec.reconstruction_version,
        spec.min_fused_score,
        spec.candidate_window,
    )
    for signal_code, signal_weight in spec.channel_weights:
        await conn.execute(
            "insert into event_lineage_rebuild_channel "
            "(rebuild_lock, signal_code, signal_weight) values (true, $1, $2)",
            signal_code,
            signal_weight,
        )
    for edge in edges:
        await conn.execute(
            "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score) "
            "values ($1::uuid, $2::uuid, $3)",
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
        )
    for row in spec.signal_rows:
        await conn.execute(
            "insert into post_lineage_edge_signal "
            "(parent_post_id, child_post_id, signal_code, signal_score, signal_weight, signal_contribution) "
            "values ($1::uuid, $2::uuid, $3, $4, $5, $6)",
            row["parent_post_id"],
            row["child_post_id"],
            row["signal_code"],
            row["signal_score"],
            row["signal_weight"],
            row["signal_contribution"],
        )


async def rebuild_lineage(
    conn: asyncpg.Connection,
    *,
    llm: AdjudicationClient | None = None,
) -> list[Edge]:
    """Reconstruct lineage for every ``source_post`` and persist the edges.

    A configured contextual-orchestrator client is passed through so the
    optional LLM channel is recorded when available; ``None`` preserves the
    fail-closed three-channel rebuild.
    """
    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    edges = lineage_edge_specs(records_from_source_posts(rows), llm=llm)
    await persist_lineage_edges(conn, edges)
    return edges


def _isoformat(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    return str(value)


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = 500,
    focus_post_id: str | None = None,
) -> dict[str, Any]:
    """ABAC-filtered graph bounded for the browser's initial viewport.

    The persisted graph can contain tens of thousands of posts. The UI opens
    individual posts for complete lineage, while this landing projection keeps
    only the newest ``limit`` visible nodes and edges between them. Channel
    evidence is attached only after both endpoints are visible.
    """
    posts = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, process_unit_id, thread_group_key, created_at "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    visible_all = [row for row in posts if can_see_post(row)]
    edge_rows = await conn.fetch(
        "select parent_post_id, child_post_id, fused_score from post_lineage_edge"
    )
    signal_rows = await conn.fetch(
        "select parent_post_id, child_post_id, signal_code, signal_score, "
        "signal_weight, signal_contribution from post_lineage_edge_signal"
    )
    rebuild_rows = await conn.fetch(
        "select reconstruction_version, generated_at, min_fused_score, candidate_window "
        "from event_lineage_rebuild"
    )
    weight_rows = await conn.fetch(
        "select channel.signal_code, channel.signal_weight "
        "from event_lineage_rebuild_channel as channel "
        "join common_lookup_value as lookup "
        "on lookup.lookup_code = channel.signal_code "
        "where channel.rebuild_lock = true "
        "order by lookup.display_order, channel.signal_code"
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

        # An isolated post has no DAG to render; the post-lineage endpoint
        # still reports its empty direct/indirect lists.
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

    signals_by_edge: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in signal_rows:
        parent_id = str(row["parent_post_id"])
        child_id = str(row["child_post_id"])
        if parent_id not in visible_ids or child_id not in visible_ids:
            continue
        payload = dict(row)
        payload["channel_name"] = LOOKUP_CODE_TO_SIGNAL.get(str(row["signal_code"]), str(row["signal_code"]))
        signals_by_edge[(parent_id, child_id)].append(payload)

    edges = [
        {
            "source": str(row["parent_post_id"]),
            "target": str(row["child_post_id"]),
            "fused_score": float(row["fused_score"]),
            "channel_evidence": rank_channel_evidence(
                signals_by_edge[(str(row["parent_post_id"]), str(row["child_post_id"]))]
            ),
        }
        for row in visible_edges
    ]
    reconstruction = None
    if rebuild_rows:
        rebuild = rebuild_rows[0]
        reconstruction = {
            "reconstruction_version": rebuild["reconstruction_version"],
            "generated_at": _isoformat(rebuild["generated_at"]),
            "min_fused_score": float(rebuild["min_fused_score"]),
            "candidate_window": int(rebuild["candidate_window"]),
            "active_weights": [
                {
                    "signal_code": LOOKUP_CODE_TO_SIGNAL.get(str(row["signal_code"]), str(row["signal_code"])),
                    "signal_weight": float(row["signal_weight"]),
                }
                for row in weight_rows
            ],
        }
    return {
        "nodes": nodes,
        "edges": edges,
        "truncated": truncated,
        "reconstruction": reconstruction,
    }

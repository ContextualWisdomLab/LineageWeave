"""Load ``source_post`` rows, run ``reconstruct``, persist ``post_lineage_edge``.

This is the product half of ``lineageweave.lineage_persistence``: the
library flattens trees; this module is the only writer of
``post_lineage_edge`` from a live database. Reconstruct grouping is
read from ``thread_group_key`` / ``secondary_grouping_key`` -- the
same keys ``reconstruct()`` was given when the posts were ingested --
not derived from process unit or voc type.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import asyncpg

from lineageweave.lineage_persistence import lineage_edge_specs
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


async def persist_run_lineage_edges(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    edges: list[Edge],
) -> None:
    """Insert run-scoped reconstruction edges. Never touches ``post_lineage_edge``.

    Rows are insert-only. Call this inside the Succeeded transaction so a
    failure rolls back a partial edge set. Does not invent a theta.
    """
    for edge in edges:
        await conn.execute(
            """
            insert into analysis_run_lineage_edge
                (analysis_run_id, parent_post_id, child_post_id, fused_score)
            values ($1::uuid, $2::uuid, $3::uuid, $4)
            """,
            analysis_run_id,
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
        )


async def persist_lineage_edges(conn: asyncpg.Connection, edges: list[Edge]) -> None:
    """Replace ``post_lineage_edge`` with ``edges`` (reconstruct is source of truth)."""
    await conn.execute("delete from post_lineage_edge")
    for edge in edges:
        await conn.execute(
            "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score) "
            "values ($1::uuid, $2::uuid, $3)",
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
        )


async def rebuild_lineage(conn: asyncpg.Connection) -> list[Edge]:
    """Reconstruct lineage for every ``source_post`` and persist the edges."""
    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        "from source_post"
    )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    await persist_lineage_edges(conn, edges)
    return edges


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
) -> dict[str, Any]:
    """ABAC-filtered ``{nodes, edges}`` matching the stdlib demo graph shape."""
    posts = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, process_unit_id, thread_group_key, created_at "
        "from source_post"
    )
    visible = [row for row in posts if can_see_post(row)]
    visible_ids = {str(row["post_id"]) for row in visible}
    edge_rows = await conn.fetch(
        "select parent_post_id, child_post_id, fused_score from post_lineage_edge"
    )
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
        }
        for row in visible_edges
    ]
    return {"nodes": nodes, "edges": edges}

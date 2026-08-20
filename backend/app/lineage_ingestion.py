"""Load ``source_post`` rows, reconstruct lineage, and persist its evidence.

This is the product half of ``lineageweave.lineage_persistence``: the
library flattens trees; this module is the only writer of
``post_lineage_edge`` and its normalized channel-evidence children from a
live database. Reconstruction grouping is read from persisted thread and
secondary keys, not derived from process unit or VOC type.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.lineage_persistence import lineage_edge_specs
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


def _validated_channel_rows(edge: Edge) -> tuple[tuple[str, float], ...]:
    """Translate one edge's channel map to deterministic database rows.

    Unknown channels and scores outside ``[0, 1]`` fail before the persisted
    edge set is replaced. A missing channel—especially optional LLM evidence—
    remains absent and is never represented by an invented zero.
    """

    rows: list[tuple[str, float]] = []
    for channel_name, raw_score in sorted(edge.channel_scores.items()):
        lookup_code = _LINEAGE_CHANNEL_LOOKUP_CODE_BY_NAME.get(channel_name)
        if lookup_code is None:
            raise ValueError(f"unsupported lineage channel: {channel_name}")
        score = float(raw_score)
        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"lineage channel score must be between 0 and 1: {channel_name}={score}"
            )
        rows.append((lookup_code, score))
    return tuple(rows)


def _public_channel_name(lookup_code: str) -> str:
    """Translate a database lookup code to the stable Buyer API key."""

    channel_name = _LINEAGE_CHANNEL_NAME_BY_LOOKUP_CODE.get(lookup_code)
    if channel_name is None:
        raise ValueError(f"unsupported persisted lineage channel: {lookup_code}")
    return channel_name


async def persist_lineage_edges(conn: asyncpg.Connection, edges: list[Edge]) -> None:
    """Replace selected edges and their exact normalized channel evidence."""

    validated_edges = [(edge, _validated_channel_rows(edge)) for edge in edges]
    await conn.execute("delete from post_lineage_edge")
    for edge, channel_rows in validated_edges:
        await conn.execute(
            "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score) "
            "values ($1::uuid, $2::uuid, $3)",
            edge.parent_id,
            edge.child_id,
            edge.fused_score,
        )
        for channel_code, channel_score in channel_rows:
            await conn.execute(
                "insert into lineage_edge_channel_score "
                "(parent_post_id, child_post_id, channel_code, channel_score) "
                "values ($1::uuid, $2::uuid, $3, $4)",
                edge.parent_id,
                edge.child_id,
                channel_code,
                channel_score,
            )


async def rebuild_lineage(conn: asyncpg.Connection) -> list[Edge]:
    """Reconstruct every eligible post and replace the persisted evidence."""

    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    await persist_lineage_edges(conn, edges)
    return edges


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = 500,
    focus_post_id: str | None = None,
) -> dict[str, Any]:
    """Return an ABAC-filtered Buyer graph with exact edge evidence.

    ``focus_post_id`` returns its complete visible connected component. The
    landing view remains bounded to the newest ``limit`` visible nodes.
    Channel scores explain reconstruction signals only; they do not make an
    inferred edge authoritative, causal, or externally verified.
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
    channel_rows = await conn.fetch(
        "select score.parent_post_id, score.child_post_id, "
        "score.channel_code, score.channel_score "
        "from lineage_edge_channel_score score "
        "join common_lookup_value lookup on lookup.lookup_code = score.channel_code "
        "order by score.parent_post_id, score.child_post_id, "
        "lookup.display_order, score.channel_code"
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

    channel_scores_by_edge: dict[tuple[str, str], dict[str, float]] = {}
    for row in channel_rows:
        parent_id = str(row["parent_post_id"])
        child_id = str(row["child_post_id"])
        if parent_id not in visible_ids or child_id not in visible_ids:
            continue
        channel_name = _public_channel_name(str(row["channel_code"]))
        channel_score = float(row["channel_score"])
        if not 0.0 <= channel_score <= 1.0:
            raise ValueError("persisted lineage channel score must be between 0 and 1")
        channel_scores_by_edge.setdefault((parent_id, child_id), {})[
            channel_name
        ] = channel_score

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
    edges = [
        {
            "source": str(row["parent_post_id"]),
            "target": str(row["child_post_id"]),
            "fused_score": float(row["fused_score"]),
            "channel_scores": channel_scores_by_edge.get(
                (str(row["parent_post_id"]), str(row["child_post_id"])),
                {},
            ),
        }
        for row in visible_edges
    ]
    return {"nodes": nodes, "edges": edges, "truncated": truncated}

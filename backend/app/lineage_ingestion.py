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
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
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


@dataclass(frozen=True)
class LineageRebuildResult:
    """One rebuild's persisted edges plus its corpus-wide coverage summary."""

    edges: list[Edge]
    coverage: dict[str, int]


def lineage_coverage_summary(
    rows: list[Mapping[str, Any]], edges: list[Edge]
) -> dict[str, int]:
    """Corpus-wide breakdown of what a rebuild actually found (ADR 0143).

    ``visible_lineage_graph`` reports this distinction per post, scoped to
    one ABAC-visible reader; this is the same distinction aggregated across
    every eligible post, for the operator who just ran the rebuild --
    counting a post as ``no_relation_found`` (its `reconstruct_group_key`
    group has other members, but it ended up with no edge) versus
    ``no_comparison_group`` (it was the only member of its group, so no
    relation could have been found either way) rather than presenting a
    reader-facing branching DAG's sparseness as undifferentiated silence.
    """
    group_sizes: dict[str, int] = {}
    for row in rows:
        group = reconstruct_group_key(row)
        group_sizes[group] = group_sizes.get(group, 0) + 1

    posts_with_edges: set[str] = set()
    for edge in edges:
        posts_with_edges.add(edge.parent_id)
        posts_with_edges.add(edge.child_id)

    posts_no_relation_found = 0
    posts_no_comparison_group = 0
    for row in rows:
        post_id = str(row["post_id"])
        if post_id in posts_with_edges:
            continue
        if group_sizes[reconstruct_group_key(row)] > 1:
            posts_no_relation_found += 1
        else:
            posts_no_comparison_group += 1

    return {
        "total_posts": len(rows),
        "posts_with_edges": len(posts_with_edges),
        "posts_no_relation_found": posts_no_relation_found,
        "posts_no_comparison_group": posts_no_comparison_group,
    }


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


async def rebuild_lineage(conn: asyncpg.Connection) -> LineageRebuildResult:
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
    await persist_lineage_edges(conn, edges)
    return LineageRebuildResult(edges=edges, coverage=lineage_coverage_summary(rows, edges))


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = 500,
    focus_post_id: str | None = None,
) -> dict[str, Any]:
    """ABAC-filtered graph bounded for the browser's initial viewport.

    The persisted graph can contain tens of thousands of posts. The UI opens
    individual posts for complete lineage, while this landing projection keeps
    only the newest ``limit`` visible nodes and edges between them.

    A focused, empty-graph result also carries ``isolation_reason`` (ADR
    0143): ``"no_relation_found"`` when the post had other visible posts in
    its ``reconstruct_group_key`` group and reconstruct still produced no
    edge, or ``"no_comparison_group"`` when it was the only visible member
    of its group. ``None`` otherwise (non-empty graph, or the landing view).
    """
    posts = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, author_account_id, source_detail_state_code, "
        "process_unit_id, thread_group_key, created_at "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    visible_all = [row for row in posts if can_see_post(row)]
    edge_rows = await conn.fetch(
        "select parent_post_id, child_post_id, fused_score from post_lineage_edge"
    )

    isolation_reason: str | None = None
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
        visible_all_ids = {str(row["post_id"]) for row in visible_all}
        neighbors: dict[str, set[str]] = {}
        for edge in edge_rows:
            parent_id = str(edge["parent_post_id"])
            child_id = str(edge["child_post_id"])
            # Both ends must be ABAC-visible: an edge to a hidden sibling
            # must not make an otherwise-isolated post look connected, nor
            # leak the mere existence of a hidden relationship through the
            # isolation_reason it would then be denied.
            if parent_id not in visible_all_ids or child_id not in visible_all_ids:
                continue
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
            # ADR 0143: distinguish "reconstruct compared this post against
            # real candidates and found no relation" from "there was
            # nothing to compare it against" -- only answerable, and only
            # meaningful, when the focused post is itself ABAC-visible. A
            # post outside `visible_all` (not visible, or nonexistent)
            # reveals nothing here, same as the empty graph it already got.
            if focus_visible:
                focus_group = reconstruct_group_key(
                    next(
                        row
                        for row in visible_all
                        if str(row["post_id"]) == focus_id
                    )
                )
                group_size = sum(
                    1
                    for row in visible_all
                    if reconstruct_group_key(row) == focus_group
                )
                isolation_reason = (
                    "no_relation_found" if group_size > 1 else "no_comparison_group"
                )
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
    edges = [
        {
            "source": str(row["parent_post_id"]),
            "target": str(row["child_post_id"]),
            "fused_score": float(row["fused_score"]),
        }
        for row in visible_edges
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "truncated": truncated,
        "isolation_reason": isolation_reason,
    }

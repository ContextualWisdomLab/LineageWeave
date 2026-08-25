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

ISOLATION_NO_COMPARISON_GROUP = "no_comparison_group"
ISOLATION_COMPARISON_CANDIDATES_AVAILABLE = "comparison_candidates_available"

# ADR 0205 authorizes only a completed, persisted TEPP criterion anchor.
_SUPPORTED_ANCHOR_METHOD_CODES: frozenset[str] = frozenset(
    {"tepp_lineage_criterion_v1"}
)


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


def focused_isolation_reason(
    focus_post_id: str | None,
    visible_posts: list[Mapping[str, Any]],
    node_count: int,
) -> str | None:
    """Why a focused Event Lineage DAG is empty (ADR 0143).

    Count only ABAC-visible group members. A hidden sibling must not
    flip ``no_comparison_group`` into candidate availability. Import
    backfills ``thread_group_key`` from process-unit code, so key
    presence is not evidence a real comparison group existed.
    """
    if focus_post_id is None or node_count > 0:
        return None
    focus_id = str(focus_post_id)
    focus_row = next(
        (row for row in visible_posts if str(row["post_id"]) == focus_id),
        None,
    )
    if focus_row is None:
        return None
    group_key = reconstruct_group_key(focus_row)
    visible_group_size = sum(
        1 for row in visible_posts if reconstruct_group_key(row) == group_key
    )
    if visible_group_size <= 1:
        return ISOLATION_NO_COMPARISON_GROUP
    # Multiple current members do not prove that the published projection
    # was rebuilt after they arrived. Report only candidate availability,
    # never a completed-comparison or no-relation conclusion.
    return ISOLATION_COMPARISON_CANDIDATES_AVAILABLE





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

    ADR 0205 authorizes only the exact persisted TEPP lineage-criterion
    contract. A partial, internally anchored, or identity-mismatched vector
    returns ``None`` rather than being repaired. A database missing either
    persistence table is likewise an unavailable state, detected without an
    aborting query inside the caller's transaction.

    Since migration 0200 one weight set is persisted per active-channel
    combination (``channel_set_code``): the corpus-wide rebuild's three
    deterministic channels and a scoped analysis run's four each match
    their own set without regressing the other. Anything other than an
    exact match of one set falls through to ``None`` -- a partial overlap
    would mix estimation runs into a vector that grounds nothing.
    """
    table_exists = await conn.fetchval(
        "select to_regclass('public.lineage_channel_weight') is not null"
    )
    if not table_exists:
        return None
    anchor_table_exists = await conn.fetchval(
        "select to_regclass('public.lineage_weight_tepp_anchor') is not null"
    )
    if not anchor_table_exists:
        return None
    # Pre-0200 schemas lack channel_set_code; probe via the catalog (never
    # a failing statement, which would abort the caller's transaction).
    # Pre-0200 rows form one implicit deterministic set.
    set_column_exists = await conn.fetchval(
        "select exists (select from information_schema.columns "
        "where table_schema = 'public' "
        "  and table_name = 'lineage_channel_weight' "
        "  and column_name = 'channel_set_code')"
    )
    set_column_sql = (
        "weight.channel_set_code" if set_column_exists else "'channel_set_deterministic'"
    )
    all_rows = await conn.fetch(
        f"select {set_column_sql} as channel_set_code, "
        "weight.channel_code, weight.weight_value, weight.estimation_run_id, "
        "weight.estimation_method_code, weight.estimator_version, weight.anchor_method_code, "
        "weight.source_snapshot_sha256, weight.sample_pair_count, weight.knowledge_cutoff, "
        "anchor.anchor_kind_code, anchor.anchor_contract_version, "
        "anchor.source_snapshot_sha256 as anchor_snapshot_sha256, "
        "anchor.knowledge_cutoff as anchor_knowledge_cutoff, "
        "anchor.criterion_validity_status_code, anchor.validated_pair_count, "
        "tepp_result.result_sha256 as tepp_result_sha256, "
        "tepp_run.run_kind_code as tepp_run_kind_code, "
        "tepp_snapshot.snapshot_sha256 as tepp_snapshot_sha256, "
        "tepp_run.knowledge_cutoff as tepp_knowledge_cutoff "
        "from lineage_channel_weight weight "
        "left join lineage_weight_tepp_anchor anchor "
        "on anchor.estimation_run_id = weight.estimation_run_id "
        "left join analysis_run_tepp_result tepp_result "
        "on tepp_result.analysis_run_id = anchor.tepp_analysis_run_id "
        "left join analysis_run tepp_run "
        "on tepp_run.analysis_run_id = tepp_result.analysis_run_id "
        "left join analysis_source_snapshot tepp_snapshot "
        "on tepp_snapshot.analysis_source_snapshot_id = tepp_run.analysis_source_snapshot_id"
    )
    sets: dict[str, list] = {}
    for row in all_rows:
        sets.setdefault(row["channel_set_code"], []).append(row)
    rows = next(
        (
            candidate
            for candidate in sets.values()
            if {row["channel_code"] for row in candidate} == active_channels
        ),
        [],
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
    if anchor_method == "tepp_lineage_criterion_v1":
        anchor_values = {
            (
                row.get("anchor_kind_code"),
                row.get("anchor_contract_version"),
                row.get("anchor_snapshot_sha256"),
                row.get("anchor_knowledge_cutoff"),
                row.get("criterion_validity_status_code"),
                row.get("validated_pair_count"),
                row.get("tepp_result_sha256"),
                row.get("tepp_run_kind_code"),
                row.get("tepp_snapshot_sha256"),
                row.get("tepp_knowledge_cutoff"),
            )
            for row in rows
        }
        if len(anchor_values) != 1:
            return None
        (
            anchor_kind,
            anchor_version,
            anchor_snapshot,
            anchor_cutoff,
            validity_status,
            validated_pairs,
            tepp_digest,
            tepp_run_kind,
            tepp_snapshot,
            tepp_cutoff,
        ) = next(iter(anchor_values))
        if (
            estimation_method != "mls2plm_expected_information"
            or anchor_kind != "lineage_pair_criterion"
            or anchor_version != 1
            or validity_status != "accepted"
            or validated_pairs != sample_pair_count
            or anchor_snapshot != snapshot_digest
            or tepp_snapshot != snapshot_digest
            or anchor_cutoff != knowledge_cutoff
            or tepp_cutoff != knowledge_cutoff
            or tepp_run_kind != "analysis_run_tepp"
            or not isinstance(tepp_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", tepp_digest) is None
        ):
            return None
    return persisted


class ChannelWeightsNotEstimated(RuntimeError):
    """No activated estimated weight set exists for the active channels.

    Product reconstruction treats fusion weights as measurement output
    only (ADR 0200 point 1): estimated by fast-mlsirm, provenance-gated,
    never hand-picked constants. No hand-picked default exists anywhere
    -- the library demo estimates its weights from its declared design,
    and unit tests inject synthetic weights explicitly.
    """

    def __init__(self, active_channels: set[str]) -> None:
        super().__init__(
            "no activated fast-mlsirm channel weight estimate exists for "
            f"active channels {sorted(active_channels)}; run "
            "scripts/estimate_channel_weights.py first -- product "
            "reconstruction never falls back to hand-picked weights"
        )
        self.active_channels = active_channels


async def rebuild_lineage(conn: asyncpg.Connection) -> list[Edge]:
    """Reconstruct lineage for every ``source_post`` and persist the edges.

    Raises :class:`ChannelWeightsNotEstimated` when no activated
    estimate matches this path's active channels -- run
    ``scripts/estimate_channel_weights.py`` first (ADR 0200 point 1).
    """
    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    # No adjudication client is wired on this path, so the active channel
    # set is the three deterministic channels (reconstruct drops llm when
    # unavailable rather than faking it).
    active_channels = {"temporal", "secondary_key", "text"}
    weights = await load_estimated_channel_weights(conn, active_channels)
    if weights is None:
        raise ChannelWeightsNotEstimated(active_channels)
    edges = lineage_edge_specs(records_from_source_posts(rows), weights=weights)
    await persist_lineage_edges(conn, edges, {str(row["post_id"]): row for row in rows})
    return edges


# Browser landing viewport and Global Ask merged-graph payload share this
# bound. Ask keeps cited posts first, then newest remaining nodes, and
# names truncation instead of shipping an unbounded component (ADR 0169).
_LINEAGE_GRAPH_NODE_LIMIT = 500


def _interval_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    code = row.get("interval_relation_code")
    if not code:
        return {}
    label = row.get("interval_relation_label") or INTERVAL_RELATION_LABELS.get(str(code))
    payload = {"interval_relation_code": str(code)}
    if label:
        payload["interval_relation_label"] = str(label)
    return payload


async def _fetch_visible_lineage_rows(conn: asyncpg.Connection, can_see_post):
    """One ABAC-filtered ``source_post`` scan plus one edge-table read."""
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
    return visible_all, edge_rows


def _undirected_neighbors(edge_rows) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = {}
    for edge in edge_rows:
        parent_id = str(edge["parent_post_id"])
        child_id = str(edge["child_post_id"])
        neighbors.setdefault(parent_id, set()).add(child_id)
        neighbors.setdefault(child_id, set()).add(parent_id)
    return neighbors


def _connected_visible_component(
    focus_id: str,
    neighbors: dict[str, set[str]],
    allowed: set[str],
) -> set[str]:
    """Walk the undirected reconstruct graph; return visible posts only.

    Invisible posts may still bridge two visible posts so the component
    matches ``visible_lineage_graph`` focus mode.
    """
    if focus_id not in allowed:
        return set()
    component_ids: set[str] = set()
    frontier = [focus_id]
    while frontier:
        current_id = frontier.pop()
        if current_id in component_ids:
            continue
        component_ids.add(current_id)
        frontier.extend(neighbors.get(current_id, set()) - component_ids)
    return component_ids & allowed


def _lineage_graph_payload(visible, edge_rows, truncated: bool) -> dict[str, Any]:
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


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = _LINEAGE_GRAPH_NODE_LIMIT,
    focus_post_id: str | None = None,
    include_isolated: bool = False,
) -> dict[str, Any]:
    """ABAC-filtered graph bounded for the browser's initial viewport.

    The persisted graph can contain tens of thousands of posts. The UI opens
    individual posts for complete lineage, while this landing projection keeps
    only the newest ``limit`` visible nodes and edges between them.
    """
    visible_all, edge_rows = await _fetch_visible_lineage_rows(conn, can_see_post)

    if focus_post_id is None:
        visible = sorted(
            visible_all,
            key=lambda row: (row["created_at"], str(row["post_id"])),
            reverse=True,
        )[:limit]
        truncated = len(visible_all) > len(visible)
    else:
        focus_id = str(focus_post_id)
        neighbors = _undirected_neighbors(edge_rows)
        allowed = {str(row["post_id"]) for row in visible_all}
        component_ids = _connected_visible_component(focus_id, neighbors, allowed)
        visible = (
            [row for row in visible_all if str(row["post_id"]) in component_ids]
            if include_isolated or len(component_ids) > 1 or focus_id in neighbors
            else []
        )
        truncated = False

    payload = _lineage_graph_payload(visible, edge_rows, truncated)
    payload["isolation_reason"] = focused_isolation_reason(
        focus_post_id, visible_all, len(visible)
    )
    return payload


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
    node_limit: int = _LINEAGE_GRAPH_NODE_LIMIT,
) -> dict[str, Any]:
    """Merge each cited post's reconstructed thread into one ``LineageGraph``.

    One ``source_post`` scan and one ``post_lineage_edge`` read cover every
    citation. Cited posts stay first when the merged graph is larger than
    ``node_limit``; ``truncated`` is then true so Ask can name the bound
    (ADR 0151 / 0169). Isolated cited posts still appear.
    """
    unique_ids = list(dict.fromkeys(str(post_id) for post_id in post_ids))
    if not unique_ids:
        return {"nodes": [], "edges": [], "truncated": False}
    visible_all, edge_rows = await _fetch_visible_lineage_rows(conn, can_see_post)
    neighbors = _undirected_neighbors(edge_rows)
    allowed = {str(row["post_id"]) for row in visible_all}
    keep_ids: set[str] = set()
    cited_visible: list[str] = []
    for post_id in unique_ids:
        component = _connected_visible_component(post_id, neighbors, allowed)
        if not component:
            continue
        keep_ids.update(component)
        cited_visible.append(post_id)
    rows_by_id = {str(row["post_id"]): row for row in visible_all}
    newest_ids = sorted(
        keep_ids,
        key=lambda pid: (rows_by_id[pid]["created_at"], pid),
        reverse=True,
    )
    ordered_ids = list(dict.fromkeys([*cited_visible, *newest_ids]))
    truncated = len(ordered_ids) > node_limit
    visible = [rows_by_id[post_id] for post_id in ordered_ids[:node_limit]]
    return _lineage_graph_payload(visible, edge_rows, truncated)

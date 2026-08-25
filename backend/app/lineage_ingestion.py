"""Load ``source_post`` rows, run ``reconstruct``, persist ``post_lineage_edge``.

This is the product half of ``lineageweave.lineage_persistence``: the
library flattens trees; this module is the only writer of
``post_lineage_edge`` from a live database. Reconstruct grouping is
read from ``thread_group_key`` / ``secondary_grouping_key`` -- the
same keys ``reconstruct()`` was given when the posts were ingested --
not derived from process unit or voc type.
"""

from __future__ import annotations

import asyncio
import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import asyncpg

from backend.app.post_eligibility import (
    SOURCE_POST_ELIGIBILITY_SQL,
    source_post_scope_sql,
)
from lineageweave.adjudication_client import AdjudicationClient
from lineageweave.interval_relation import (
    INTERVAL_RELATION_LABELS,
    allen_interval_relation,
    interval_from_post,
    interval_relation_from_current,
)
from lineageweave.lineage_persistence import (
    LOOKUP_CODE_TO_SIGNAL,
    lineage_edge_specs,
    lineage_rebuild_spec,
    rank_channel_evidence,
)
from lineageweave.models import Edge, Record
from lineageweave.reconstruct import DEFAULT_CANDIDATE_WINDOW

MAXIMUM_LIVE_LLM_PAIR_EVALUATIONS = 5_000

ISOLATION_NO_COMPARISON_GROUP = "no_comparison_group"
ISOLATION_COMPARISON_CANDIDATES_AVAILABLE = "comparison_candidates_available"

# ADR 0205 authorizes only a completed, persisted TEPP criterion anchor.
_SUPPORTED_ANCHOR_METHOD_CODES: frozenset[str] = frozenset(
    {"tepp_lineage_criterion_v1"}
)

_LINEAGE_LANDING_SQL = (
    "select post_id, post_title, voc_type_code, visibility_code, "
    "corporate_entity_id, process_unit_id, thread_group_key, created_at "
    "from source_post where {eligibility} and {visibility} "
    "order by created_at desc, post_id desc limit $3"
).format(
    eligibility=SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post"),
    visibility=source_post_scope_sql("source_post"),
)

def estimated_weight_channels(llm: AdjudicationClient | None) -> set[str]:
    """Return the channels that one live reconstruction can actually use."""
    channels = {"temporal", "secondary_key", "text"}
    if getattr(llm, "available", False):
        channels.add("llm")
    return channels


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
    weights: dict[str, float],
    points_by_post_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    """Replace live Event Lineage with edges, channel evidence, and intervals.

    Reconstruct is the source of truth. The delete is cascaded onto
    ``post_lineage_edge_signal`` so a rebuild cannot leave orphan or
    stale signal rows. Rebuild metadata is replaced in the same
    connection so version, weights, and generated-at stay aligned with
    the new graph.
    """
    points = points_by_post_id or {}
    missing_point_ids = {
        post_id
        for edge in edges
        for post_id in (edge.parent_id, edge.child_id)
        if post_id not in points
    }
    if missing_point_ids:
        raise ValueError(
            "missing observed interval point for post ids: "
            + ", ".join(sorted(missing_point_ids))
        )
    spec = lineage_rebuild_spec(edges, weights=weights)
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
    await conn.executemany(
        "insert into event_lineage_rebuild_channel "
        "(rebuild_lock, signal_code, signal_weight) values (true, $1, $2)",
        spec.channel_weights,
    )
    await conn.executemany(
        "insert into post_lineage_edge "
        "(parent_post_id, child_post_id, fused_score, interval_relation_code) "
        "values ($1::uuid, $2::uuid, $3, $4)",
        [
            (
                edge.parent_id,
                edge.child_id,
                edge.fused_score,
                interval_relation_code_for_edge(
                    points[edge.parent_id], points[edge.child_id]
                ),
            )
            for edge in edges
        ],
    )
    await conn.executemany(
        "insert into post_lineage_edge_signal "
        "(parent_post_id, child_post_id, signal_code, signal_score, signal_weight, signal_contribution) "
        "values ($1::uuid, $2::uuid, $3, $4, $5, $6)",
        [
            (
                row["parent_post_id"],
                row["child_post_id"],
                row["signal_code"],
                row["signal_score"],
                row["signal_weight"],
                row["signal_contribution"],
            )
            for row in spec.signal_rows
        ],
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
    matching_sets = [
        candidate
        for candidate in sets.values()
        if {row["channel_code"] for row in candidate} == active_channels
    ]
    if len(matching_sets) != 1:
        return None
    rows = matching_sets[0]
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
    and tests use provenance-bearing estimates.
    """

    def __init__(self, active_channels: set[str]) -> None:
        super().__init__(
            "no activated fast-mlsirm channel weight estimate exists for "
            f"active channels {sorted(active_channels)}; run "
            "scripts/estimate_channel_weights.py first -- product "
            "reconstruction never falls back to hand-picked weights"
        )
        self.active_channels = active_channels


async def _load_lineage_records(conn: asyncpg.Connection) -> list[Record]:
    """Load the eligible source snapshot used by one reconstruction."""
    rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
        "process_unit_id, thread_group_key, secondary_grouping_key "
        f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
    )
    return records_from_source_posts(rows)


def _budgeted_llm(
    records: list[Record], llm: AdjudicationClient | None
) -> AdjudicationClient | None:
    """Drop adjudication before weight lookup when the pair budget is exceeded."""
    pair_count = 0
    records_per_group: defaultdict[str, int] = defaultdict(int)
    for record in records:
        pair_count += min(records_per_group[record.group_key], DEFAULT_CANDIDATE_WINDOW)
        if pair_count > MAXIMUM_LIVE_LLM_PAIR_EVALUATIONS:
            return None
        records_per_group[record.group_key] += 1
    return llm


async def _reconstruct_lineage_records(
    records: list[Record],
    llm: AdjudicationClient | None,
    weights: dict[str, float],
) -> list[Edge]:
    """Run the CPU/provider reconstruction without blocking the event loop."""
    llm = _budgeted_llm(records, llm)
    return await asyncio.to_thread(lineage_edge_specs, records, llm=llm, weights=weights)


async def rebuild_lineage(
    conn: asyncpg.Connection,
    *,
    llm: AdjudicationClient | None = None,
) -> list[Edge]:
    """Reconstruct lineage for every ``source_post`` and persist the edges.

    The adjudication channel is dropped before weight lookup when the exact
    candidate-pair work exceeds the ADR 0172 budget. The resulting active
    channel set must have a provenance-gated fast-mlsirm estimate; there is no
    hand-picked fallback (ADR 0200).
    """
    records = await _load_lineage_records(conn)
    llm = _budgeted_llm(records, llm)
    active_channels = estimated_weight_channels(llm)
    weights = await load_estimated_channel_weights(conn, active_channels)
    if weights is None:
        raise ChannelWeightsNotEstimated(active_channels)
    edges = await _reconstruct_lineage_records(records, llm, weights)
    points = {record.record_id: {"created_at": record.occurred_at} for record in records}
    async with conn.transaction():
        await persist_lineage_edges(conn, edges, weights, points)
    return edges


async def rebuild_lineage_from_pool(
    pool: asyncpg.Pool,
    *,
    llm: AdjudicationClient | None = None,
) -> list[Edge]:
    """Reconstruct without holding a pooled connection during provider work.

    The source snapshot is read and released first. Only the replacement
    writes run in a transaction, preserving ADR 0172 atomicity without an
    idle-in-transaction connection during CPU or orchestrator calls.
    """
    async with pool.acquire() as conn:
        records = await _load_lineage_records(conn)
        llm = _budgeted_llm(records, llm)
        active_channels = estimated_weight_channels(llm)
        weights = await load_estimated_channel_weights(conn, active_channels)
        if weights is None:
            raise ChannelWeightsNotEstimated(active_channels)
    edges = await _reconstruct_lineage_records(records, llm, weights)
    points = {record.record_id: {"created_at": record.occurred_at} for record in records}
    async with pool.acquire() as conn, conn.transaction():
        await persist_lineage_edges(conn, edges, weights, points)
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
    posts = await conn.fetch(  # nosemgrep
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


async def _fetch_lineage_landing_rows(
    conn: asyncpg.Connection,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
    limit: int,
):
    """Fetch only the authorized, bounded landing projection in PostgreSQL."""
    # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
    # `_LINEAGE_LANDING_SQL` is a module constant; all runtime values below
    # use asyncpg bind parameters. No caller-controlled SQL is interpolated.
    posts = await conn.fetch(  # nosemgrep
        _LINEAGE_LANDING_SQL,
        list(corporate_entity_ids),
        list(process_unit_ids),
        limit + 1,
    )
    visible = list(posts[:limit])
    visible_ids = [str(row["post_id"]) for row in visible]
    edge_rows = (
        await conn.fetch(
            "select parent_post_id, child_post_id, fused_score, interval_relation_code "
            "from post_lineage_edge where parent_post_id = any($1::uuid[]) "
            "and child_post_id = any($1::uuid[])",
            visible_ids,
        )
        if visible_ids
        else []
    )
    return visible, edge_rows, len(posts) > limit


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

    Invisible posts cannot bridge visible posts across the ABAC boundary.
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
        frontier.extend((neighbors.get(current_id, set()) & allowed) - component_ids)
    return component_ids


async def _lineage_graph_payload(
    conn: asyncpg.Connection, visible, edge_rows, truncated: bool
) -> dict[str, Any]:
    """Build a channel-auditable graph from already authorized rows."""
    visible_ids = {str(row["post_id"]) for row in visible}
    visible_edges = [
        row
        for row in edge_rows
        if str(row["parent_post_id"]) in visible_ids and str(row["child_post_id"]) in visible_ids
    ]
    visible_id_list = sorted(visible_ids)
    signal_rows = await conn.fetch(
        "select parent_post_id, child_post_id, signal_code, signal_score, "
        "signal_weight, signal_contribution from post_lineage_edge_signal "
        "where parent_post_id = any($1::uuid[]) "
        "and child_post_id = any($2::uuid[])",
        visible_id_list,
        visible_id_list,
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
            **_interval_payload(row),
        }
        for row in visible_edges
    ]
    reconstruction = None
    if rebuild_rows:
        rebuild = rebuild_rows[0]
        reconstruction = {
            "reconstruction_version": rebuild["reconstruction_version"],
            "generated_at": rebuild["generated_at"].isoformat(),
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


async def visible_lineage_graph(
    conn: asyncpg.Connection,
    can_see_post,
    limit: int = _LINEAGE_GRAPH_NODE_LIMIT,
    focus_post_id: str | None = None,
    include_isolated: bool = False,
    corporate_entity_ids: Sequence[str] | None = None,
    process_unit_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """ABAC-filtered graph bounded for the browser's initial viewport.

    The persisted graph can contain tens of thousands of posts. The UI opens
    individual posts for complete lineage, while this landing projection keeps
    only the newest ``limit`` visible nodes and edges between them.
    """
    if focus_post_id is None and corporate_entity_ids is not None:
        visible, edge_rows, truncated = await _fetch_lineage_landing_rows(
            conn, corporate_entity_ids, process_unit_ids, limit
        )
        visible_all = visible
    else:
        visible_all, edge_rows = await _fetch_visible_lineage_rows(conn, can_see_post)

    if focus_post_id is None and corporate_entity_ids is None:
        visible = sorted(
            visible_all,
            key=lambda row: (row["created_at"], str(row["post_id"])),
            reverse=True,
        )[:limit]
        truncated = len(visible_all) > len(visible)
    elif focus_post_id is not None:
        focus_id = str(focus_post_id)
        neighbors = _undirected_neighbors(edge_rows)
        allowed = {str(row["post_id"]) for row in visible_all}
        component_ids = _connected_visible_component(focus_id, neighbors, allowed)
        visible = (
            [row for row in visible_all if str(row["post_id"]) in component_ids]
            if include_isolated or len(component_ids) > 1
            else []
        )
        truncated = False

    payload = await _lineage_graph_payload(conn, visible, edge_rows, truncated)
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
        return {
            "nodes": [],
            "edges": [],
            "truncated": False,
            "reconstruction": None,
        }
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
    return await _lineage_graph_payload(conn, visible, edge_rows, truncated)

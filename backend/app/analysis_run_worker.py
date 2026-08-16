"""Start a queued lineage reconstruction from the analysis-run outbox.

ADR 0018. ``POST /api/analysis-runs`` stays Pending-only and never invents
a TEPP score. This worker claims the PostgreSQL outbox, reconstructs the
authorized cutoff bag through ThreadWeave / RankWeave, persists
run-scoped edges, and appends Running then Succeeded or Failed.

It does not call ``rebuild_lineage`` and does not delete live
``post_lineage_edge`` rows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import asyncpg

from backend.app.analysis_run_ingestion import fetch_visible_analysis_run
from backend.app.analysis_run_outbox import (
    AnalysisRunDeliveryError,
    claim_lineage_delivery,
    complete_lineage_delivery,
    fail_lineage_delivery,
)
from backend.app.lineage_ingestion import (
    persist_run_lineage_edges,
    records_from_source_posts,
)
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge, Record

LINEAGE_RUN_KIND = "analysis_run_lineage"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"
_FAILED = "analysis_status_failed"
_PENDING = "analysis_status_pending"
RECONSTRUCTION_FAILED = "lineage_reconstruction_failed"


def reconstruct_cutoff_edges(records: list[Record]) -> list[Edge]:
    """Recover parent→child edges for one cutoff bag.

    The designed A-100 fixture must still fork at the pricing-renegotiation
    follow-up. This function does not invent identifiers or a theta.
    """
    return lineage_edge_specs(records)


async def _current_status(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> asyncpg.Record | None:
    """Latest append-only status row, or None when the run is missing."""
    return await conn.fetchrow(
        """
        select run.run_kind_code,
               run.knowledge_cutoff,
               scope.corporate_entity_id,
               status.status_code,
               status.status_ordinal
          from analysis_run run
          join analysis_run_scope scope
            on scope.analysis_run_id = run.analysis_run_id
          left join analysis_run_current_status status
            on status.analysis_run_id = run.analysis_run_id
         where run.analysis_run_id = $1
        """,
        analysis_run_id,
    )


async def _append_status(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    status_ordinal: int,
    status_code: str,
    occurred_at: datetime,
    failure_code: str | None = None,
) -> None:
    """Append one legal lifecycle event. Failed events need a machine code."""
    await conn.execute(
        """
        insert into analysis_run_status_event
            (analysis_run_id, status_ordinal, status_code, occurred_at, failure_code)
        values ($1, $2, $3, $4, $5)
        """,
        analysis_run_id,
        status_ordinal,
        status_code,
        occurred_at,
        failure_code,
    )


async def _cutoff_source_posts(
    conn: asyncpg.Connection,
    corporate_entity_id: str,
    knowledge_cutoff: datetime,
    affiliated_entity_ids: list[str],
) -> list[asyncpg.Record]:
    """ABAC-visible posts at or before the run cutoff — never a hidden body."""
    rows = await conn.fetch(
        """
        select post_id, post_title, voc_type_code, created_at,
               corporate_entity_id, process_unit_id,
               thread_group_key, secondary_grouping_key, visibility_code
          from source_post
         where corporate_entity_id = $1
           and created_at <= $2
         order by created_at, post_title
        """,
        corporate_entity_id,
        knowledge_cutoff,
    )
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    return [
        row
        for row in rows
        if row["visibility_code"] == "public"
        or str(row["corporate_entity_id"]) in affiliated
    ]


async def deliver_pending_lineage_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Claim the outbox, reconstruct the cutoff bag, and advance lifecycle.

    TEPP rows are rejected. A replay of a Succeeded lineage run returns
    the authorized detail without writing a second edge set.
    """
    visible = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if visible is None:
        raise AnalysisRunDeliveryError(404, "This analysis run is not visible.")
    if visible["run_kind_code"] != LINEAGE_RUN_KIND:
        raise AnalysisRunDeliveryError(
            422,
            "Connect a TEPP transport from a Failed TEPP row. This path reconstructs lineage only.",
        )
    if visible["status_code"] == _SUCCEEDED:
        return visible
    if visible["status_code"] == _FAILED:
        raise AnalysisRunDeliveryError(
            422,
            "Open this run to see why it failed, then retry reconstruction from a current snapshot.",
        )
    if visible["status_code"] not in {_PENDING, _RUNNING}:
        raise AnalysisRunDeliveryError(
            422,
            "Open this run, then start reconstruction from a Pending lineage row.",
        )

    lease_token = await claim_lineage_delivery(conn, analysis_run_id)
    if lease_token == "":
        return visible
    current = await _current_status(conn, analysis_run_id)
    if current is None:
        await fail_lineage_delivery(conn, analysis_run_id, lease_token)
        raise AnalysisRunDeliveryError(404, "This analysis run is not visible.")

    now = datetime.now(timezone.utc)
    next_ordinal = int(current["status_ordinal"] or 0) + 1
    try:
        if current["status_code"] == _PENDING:
            await _append_status(conn, analysis_run_id, next_ordinal, _RUNNING, now)
            next_ordinal += 1
        posts = await _cutoff_source_posts(
            conn,
            str(current["corporate_entity_id"]),
            current["knowledge_cutoff"],
            affiliated_entity_ids,
        )
        records = records_from_source_posts(posts)
        edges = reconstruct_cutoff_edges(records)
        await persist_run_lineage_edges(conn, analysis_run_id, edges)
        await _append_status(conn, analysis_run_id, next_ordinal, _SUCCEEDED, now)
        await complete_lineage_delivery(conn, analysis_run_id, lease_token)
    except AnalysisRunDeliveryError:
        raise
    except Exception:
        await fail_lineage_delivery(conn, analysis_run_id, lease_token)
        fail_ordinal = next_ordinal
        latest = await _current_status(conn, analysis_run_id)
        if latest is not None and latest["status_code"] == _RUNNING:
            fail_ordinal = int(latest["status_ordinal"]) + 1
            await _append_status(
                conn,
                analysis_run_id,
                fail_ordinal,
                _FAILED,
                datetime.now(timezone.utc),
                RECONSTRUCTION_FAILED,
            )
        raise AnalysisRunDeliveryError(
            422,
            "Open this run to see why it failed, then retry reconstruction from a current snapshot.",
        ) from None

    delivered = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if delivered is None:
        raise AnalysisRunDeliveryError(404, "This analysis run is not visible.")
    return delivered

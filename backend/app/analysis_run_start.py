"""Start a Pending lineage reconstruction without inventing a TEPP score.

ADR 0019. ``POST /api/analysis-runs/{id}/start`` transitions Pending to
Running, runs ThreadWeave on the authorized cutoff bag, persists
run-scoped edges, then stamps Succeeded. TEPP stays a wire client.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    fetch_visible_analysis_run,
)
from backend.app.lineage_ingestion import records_from_source_posts
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge

_LINEAGE_KIND = "analysis_run_lineage"
_PENDING = "analysis_status_pending"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"


class AnalysisRunStartError(AnalysisRunCreateError):
    """Fail-closed start: HTTP status plus a next-action detail string."""


def reconstruction_result_digest(edges: list[Edge]) -> str:
    """SHA-256 of the ordered parent choices. Never hashes a post body."""
    material = json.dumps(
        [
            {
                "child_post_id": edge.child_id,
                "fused_score": round(float(edge.fused_score), 6),
                "parent_post_id": edge.parent_id,
            }
            for edge in sorted(edges, key=lambda item: (item.child_id, item.parent_id))
        ],
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


async def _cutoff_source_posts(
    conn: asyncpg.Connection,
    *,
    corporate_entity_id: Any,
    knowledge_cutoff: Any,
    affiliated_entity_ids: list[str],
) -> list[asyncpg.Record]:
    """ABAC-visible cutoff rows with the grouping keys reconstruct needs."""
    rows = await conn.fetch(
        """
        select post_id, post_title, created_at, visibility_code,
               corporate_entity_id, process_unit_id,
               thread_group_key, secondary_grouping_key
        from source_post
        where corporate_entity_id = $1 and created_at <= $2
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


async def _append_status(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    status_ordinal: int,
    status_code: str,
    occurred_at: datetime,
    failure_code: str | None = None,
) -> None:
    """Append one legal lifecycle event. Failed rows carry a machine code."""
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


async def start_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Run ThreadWeave on a visible Pending lineage row.

    TEPP is rejected so this path cannot invent a theta. A Succeeded
    retry returns the stored reconstruction. Hidden runs 404.
    """
    try:
        UUID(analysis_run_id)
    except ValueError as exc:
        raise AnalysisRunStartError(404, "This analysis run is not visible.") from exc

    current = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if current is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    if current["run_kind_code"] != _LINEAGE_KIND:
        raise AnalysisRunStartError(
            422,
            "Connect a TEPP transport from a Failed TEPP row. "
            "This start path does not invent a measurement.",
        )
    if current["status_code"] == _SUCCEEDED:
        return current
    if current["status_code"] != _PENDING:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction.",
        )

    now = datetime.now(timezone.utc)
    await _append_status(conn, analysis_run_id, 2, _RUNNING, now)

    locked = await conn.fetchrow(
        """
        select run.analysis_run_id, run.knowledge_cutoff,
               scope.corporate_entity_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        where run.analysis_run_id = $1
        for update of run
        """,
        analysis_run_id,
    )
    rows = await _cutoff_source_posts(
        conn,
        corporate_entity_id=locked["corporate_entity_id"],
        knowledge_cutoff=locked["knowledge_cutoff"],
        affiliated_entity_ids=affiliated_entity_ids,
    )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    digest = reconstruction_result_digest(edges)
    finished = datetime.now(timezone.utc)
    if finished < now:
        finished = now
    await conn.execute(
        """
        insert into analysis_run_reconstruction
            (analysis_run_id, result_sha256, edge_count, reconstructed_at)
        values ($1, $2, $3, $4)
        """,
        analysis_run_id,
        digest,
        len(edges),
        finished,
    )
    for edge in edges:
        await conn.execute(
            """
            insert into analysis_run_lineage_edge
                (analysis_run_id, child_post_id, parent_post_id,
                 fused_score, reconstructed_at)
            values ($1, $2, $3, $4, $5)
            """,
            analysis_run_id,
            edge.child_id,
            edge.parent_id,
            edge.fused_score,
            finished,
        )
    await _append_status(conn, analysis_run_id, 3, _SUCCEEDED, finished)
    started = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if started is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return started

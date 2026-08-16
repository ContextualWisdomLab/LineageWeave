"""Start a Pending lineage reconstruction or TEPP measurement.

ADR 0021 reconstructs lineage. ADR 0022 starts TEPP through
``tepp_client`` only. Period-report stays another path. Neither start
invents a theta or a calibrated report score.
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
from lineageweave.http_client import HttpClientError, post_json
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

_LINEAGE_KIND = "analysis_run_lineage"
_TEPP_KIND = "analysis_run_tepp"
_REPORT_KIND = "analysis_run_report"
_PENDING = "analysis_status_pending"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"
_FAILED = "analysis_status_failed"
_TEPP_MODEL_CONTRACT = "tepp-analysis-run-v1"
_TEPP_OUTPUT_PROFILE = "calibrated_event_measurement"


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


def start_kind_rejection(run_kind_code: str) -> AnalysisRunStartError | None:
    """Return a 422 when start cannot run this kind.

    Lineage reconstructs the frozen bag. TEPP submits through
    ``tepp_client`` and never invents a theta. Period-report stays on
    its own rebuild path.
    """
    if run_kind_code in {_LINEAGE_KIND, _TEPP_KIND}:
        return None
    if run_kind_code == _REPORT_KIND:
        return AnalysisRunStartError(
            422,
            "Rebuild the period report from the reports panel. "
            "This start path does not invent a measurement.",
        )
    return AnalysisRunStartError(
        422,
        "Start reconstructs a Pending lineage run or submits TEPP. "
        "This start path does not invent a measurement.",
    )


def configured_tepp_client(transport_url: str = "") -> TeppClient:
    """Build a TEPP client from an optional HTTP transport URL.

    An empty URL keeps the default unavailable transport. A set URL
    POSTs TEPP's published wire payload. File URLs and other schemes
    stay unavailable -- this is not a local psychometric substitute.
    """
    url = transport_url.strip()
    if not url:
        return TeppClient()

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return post_json(url, payload, headers={}, timeout=30.0)
        except (HttpClientError, ValueError, TypeError) as exc:
            raise TeppNotAvailable(str(exc)) from exc

    return TeppClient(transport=transport)


def tepp_run_request(
    *,
    idempotency_key: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
    corporate_entity_id: str,
) -> AnalysisRunRequest:
    """Build TEPP's published request from the frozen run, never a theta."""
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=str(corporate_entity_id),
        snapshot_id=snapshot_sha256,
        knowledge_cutoff=cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_contract_version=_TEPP_MODEL_CONTRACT,
        output_profile=_TEPP_OUTPUT_PROFILE,
    )


def tepp_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str]:
    """Submit through ``tepp_client``. Never invent or persist a theta.

    A missing transport is ``tepp_not_available``. An accepted envelope
    is not a persistable measurement until TEPP publishes one, so the
    run stays Failed / ``tepp_result_not_persisted``.
    """
    try:
        client.submit_analysis_run(request)
    except TeppNotAvailable:
        return _FAILED, "tepp_not_available"
    return _FAILED, "tepp_result_not_persisted"


def start_write_conflict_error() -> AnalysisRunStartError:
    """Next action when a concurrent start already wrote this run."""
    return AnalysisRunStartError(
        409,
        "Open this run. Refresh to see the stored tree if start already finished.",
    )


def reconstruction_member_ids(
    snapshot_member_ids: list[str],
    cutoff_post_ids: list[str],
) -> list[str]:
    """Prefer create-time membership over a later cutoff re-query.

    An empty member list means this database has not frozen the bag yet
    (migration 0022 missing, or a legacy snapshot). Start then uses the
    live cutoff query so those rows still reconstruct.
    """
    if snapshot_member_ids:
        return list(snapshot_member_ids)
    return list(cutoff_post_ids)


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


async def _snapshot_member_posts(
    conn: asyncpg.Connection,
    snapshot_id: Any,
) -> list[asyncpg.Record]:
    """Load frozen capture rows, or empty when the member table is absent."""
    try:
        return list(
            await conn.fetch(
                """
                select post.post_id, post.post_title, post.created_at,
                       post.visibility_code, post.corporate_entity_id,
                       post.process_unit_id, post.thread_group_key,
                       post.secondary_grouping_key
                from analysis_source_snapshot_member member
                join source_post post on post.post_id = member.source_post_id
                where member.analysis_source_snapshot_id = $1
                order by post.created_at, post.post_title
                """,
                snapshot_id,
            )
        )
    except asyncpg.UndefinedTableError:
        return []


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


async def _next_status_ordinal(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> int:
    """Return the next contiguous status ordinal for this run."""
    current_max = await conn.fetchval(
        """
        select coalesce(max(status_ordinal), 0)
        from analysis_run_status_event
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    return int(current_max) + 1


async def start_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
) -> dict[str, Any]:
    """Run ThreadWeave or submit TEPP on a visible Pending row.

    Period-report is rejected so this path cannot invent a calibrated
    score. TEPP goes through ``tepp_client`` and stays Failed when the
    transport is missing or the envelope is not persistable. A Succeeded
    retry returns the stored reconstruction (documented no-op replay).
    A Running or concurrent write is 409. Hidden runs 404. The run row
    is locked before Running so a double-click is 409 or a replay,
    never a 500.
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
    kind_error = start_kind_rejection(current["run_kind_code"])
    if kind_error is not None:
        raise kind_error
    if current["status_code"] == _SUCCEEDED:
        return current
    if current["status_code"] != _PENDING:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )

    locked = await conn.fetchrow(
        """
        select run.analysis_run_id, run.knowledge_cutoff, run.run_kind_code,
               run.idempotency_key, run.analysis_source_snapshot_id,
               snapshot.snapshot_sha256, scope.corporate_entity_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where run.analysis_run_id = $1
        for update of run
        """,
        analysis_run_id,
    )
    locked_status = await conn.fetchval(
        """
        select status_code
        from analysis_run_current_status
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    if locked_status == _SUCCEEDED:
        replayed = await fetch_visible_analysis_run(
            conn,
            analysis_run_id,
            account_id,
            affiliated_entity_ids,
        )
        if replayed is None:
            raise AnalysisRunStartError(404, "This analysis run is not visible.")
        return replayed
    if locked_status != _PENDING:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )

    if locked["run_kind_code"] == _TEPP_KIND:
        return await _start_tepp_measurement(
            conn,
            analysis_run_id=analysis_run_id,
            account_id=account_id,
            affiliated_entity_ids=affiliated_entity_ids,
            locked=locked,
            tepp_client=tepp_client or TeppClient(),
        )

    now = datetime.now(timezone.utc)
    running_ordinal = await _next_status_ordinal(conn, analysis_run_id)
    try:
        await _append_status(conn, analysis_run_id, running_ordinal, _RUNNING, now)
        member_rows = await _snapshot_member_posts(
            conn,
            locked["analysis_source_snapshot_id"],
        )
        if member_rows:
            rows = member_rows
        else:
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
        await _append_status(
            conn,
            analysis_run_id,
            running_ordinal + 1,
            _SUCCEEDED,
            finished,
        )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    started = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if started is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return started


async def _start_tepp_measurement(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    locked: asyncpg.Record,
    tepp_client: TeppClient,
) -> dict[str, Any]:
    """Submit the frozen snapshot through ``tepp_client``. Never persist a theta."""
    now = datetime.now(timezone.utc)
    running_ordinal = await _next_status_ordinal(conn, analysis_run_id)
    try:
        await _append_status(conn, analysis_run_id, running_ordinal, _RUNNING, now)
        request = tepp_run_request(
            idempotency_key=str(locked["idempotency_key"]),
            snapshot_sha256=str(locked["snapshot_sha256"]),
            knowledge_cutoff=locked["knowledge_cutoff"],
            corporate_entity_id=str(locked["corporate_entity_id"]),
        )
        status_code, failure_code = tepp_submit_outcome(tepp_client, request)
        finished = datetime.now(timezone.utc)
        if finished < now:
            finished = now
        await _append_status(
            conn,
            analysis_run_id,
            running_ordinal + 1,
            status_code,
            finished,
            failure_code,
        )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    started = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if started is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return started

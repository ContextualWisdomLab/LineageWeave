"""Start a Pending lineage reconstruction or TEPP measurement.

ADR 0021 reconstructs lineage. ADR 0022 starts TEPP through
``tepp_client`` only. ADR 0023 enqueues that work on a durable outbox
so a crash after Running does not lose the item. Period-report stays
another path. Neither start invents a theta or a calibrated report
score.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import asyncpg

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    fetch_visible_analysis_run,
)
from backend.app.analysis_run_outbox import (
    latest_outbox_delivery_is_claimed,
    latest_outbox_delivery_is_delivered,
    outbox_request_digest,
)
from backend.app.lineage_ingestion import records_from_source_posts
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.adjudication_client import AdjudicationClient
from lineageweave.http_client import post_json
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

_LINEAGE_KIND = "analysis_run_lineage"
_TEPP_KIND = "analysis_run_tepp"
_REPORT_KIND = "analysis_run_report"
_TOPIC_LINEAGE_KIND = "analysis_run_topic_lineage"
_PENDING = "analysis_status_pending"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"
_FAILED = "analysis_status_failed"
_TEPP_MODEL_CONTRACT = "tepp-analysis-run-v1"
_TEPP_OUTPUT_PROFILE = "calibrated_event_measurement"
_TOPIC_LINEAGE_MODEL_CONTRACT = "tepp-topic-lineage-v1"
_TOPIC_LINEAGE_OUTPUT_PROFILE = "topic_identity_lineage"


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

    Lineage reconstructs the frozen bag. TEPP and topic-lineage submit
    through ``tepp_client`` and never invent a theta or a topic (ADR 0022 /
    ADR 0132). Period-report stays on its own rebuild path.
    """
    if run_kind_code in {_LINEAGE_KIND, _TEPP_KIND, _TOPIC_LINEAGE_KIND}:
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


def configured_tepp_client(transport_url: str = "", api_key: str = "") -> TeppClient:
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
            headers = {"authorization": f"Bearer {api_key}"} if api_key.strip() else {}
            return post_json(url, payload, headers=headers, timeout=30.0)
        except Exception as exc:
            raise TeppNotAvailable("TEPP transport request failed") from exc

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
        cutoff = cutoff.replace(tzinfo=UTC)
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=str(corporate_entity_id),
        snapshot_id=snapshot_sha256,
        knowledge_cutoff=cutoff.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_contract_version=_TEPP_MODEL_CONTRACT,
        output_profile=_TEPP_OUTPUT_PROFILE,
    )


def topic_lineage_run_request(
    *,
    idempotency_key: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
    corporate_entity_id: str,
) -> AnalysisRunRequest:
    """Build TEPP's published request for a topic-lineage run (ADR 0132).

    Same wire shape as :func:`tepp_run_request` -- TEPP's
    ``AnalysisRunRequest`` already carries no post body or fabricated
    label -- only the model contract and output profile differ, selecting
    TRSL-TM topic identity plus CHRONOS/TDT event-intelligence status
    instead of calibrated psychometric measurement.
    """
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=str(corporate_entity_id),
        snapshot_id=snapshot_sha256,
        knowledge_cutoff=cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_contract_version=_TOPIC_LINEAGE_MODEL_CONTRACT,
        output_profile=_TOPIC_LINEAGE_OUTPUT_PROFILE,
    )


def _tepp_submission(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str, dict[str, Any] | None]:
    """Submit through ``tepp_client`` and require a completed result envelope.

    TEPP's target HTTP contract is asynchronous. An ``accepted`` response is
    therefore not a measurement and remains ``tepp_result_not_persisted``.
    Only a provider-authoritative completed envelope can enter the database.
    """
    try:
        response = client.submit_analysis_run(request)
    except TeppNotAvailable:
        return _FAILED, "tepp_not_available", None
    if not isinstance(response, dict):
        return _FAILED, "tepp_result_not_persisted", None
    if response.get("status") not in {"completed", "succeeded"}:
        return _FAILED, "tepp_result_not_persisted", None
    if not isinstance(response.get("result"), dict):
        return _FAILED, "tepp_result_not_persisted", None
    remote_run_id = response.get("analysis_run_id") or response.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return _FAILED, "tepp_result_not_persisted", None
    return _SUCCEEDED, "", response


def tepp_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str]:
    """Compatibility projection of the TEPP submission outcome."""
    status_code, failure_code, _ = _tepp_submission(client, request)
    return status_code, failure_code


async def _persist_tepp_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
) -> bool:
    """Persist only a validated, remote-completed TEPP envelope."""
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return False
    result_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    result_sha256 = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                insert into analysis_run_tepp_result
                    (analysis_run_id, remote_run_id, result_json, result_sha256)
                values ($1, $2, $3::jsonb, $4)
                on conflict (analysis_run_id) do nothing
                """,
                analysis_run_id,
                remote_run_id,
                result_json,
                result_sha256,
            )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


async def _persist_topic_lineage_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
) -> bool:
    """Persist only a validated, remote-completed topic-lineage envelope.

    Stores TEPP's TRSL-TM topic identity / CHRONOS status envelope
    verbatim (ADR 0132); LineageWeave does not decompose or reinterpret
    its evidence/inference/prediction fields here.
    """
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return False
    result_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    result_sha256 = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                insert into analysis_run_topic_lineage_result
                    (analysis_run_id, remote_run_id, result_json, result_sha256)
                values ($1, $2, $3::jsonb, $4)
                on conflict (analysis_run_id) do nothing
                """,
                analysis_run_id,
                remote_run_id,
                result_json,
                result_sha256,
            )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


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
    # Safe SQL: the eligibility predicate is an immutable schema fragment; both request values are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, created_at, visibility_code,
               corporate_entity_id, process_unit_id,
               thread_group_key, secondary_grouping_key
        from source_post
        where corporate_entity_id = $1
          and created_at <= $2
          and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}
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
            # Safe SQL: the eligibility predicate is an immutable schema fragment; snapshot id is bound.
            await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                f"""
                select post.post_id, post.post_title, post.created_at,
                       post.visibility_code, post.corporate_entity_id,
                       post.process_unit_id, post.thread_group_key,
                       post.secondary_grouping_key
                from analysis_source_snapshot_member member
                join source_post post
                  on post.post_id = member.source_post_id
                 and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
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
        values ($1, $2, $3, clock_timestamp(), $4)
        """,
        analysis_run_id,
        status_ordinal,
        status_code,
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


async def _latest_outbox_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> str | None:
    """Newest outbox delivery status, or None when the row was never claimed."""
    return await conn.fetchval(
        """
        select delivery_status_code
        from analysis_run_outbox_delivery
        where analysis_run_id = $1
        order by delivery_ordinal desc
        limit 1
        """,
        analysis_run_id,
    )


async def _next_outbox_delivery_ordinal(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> int:
    """Return the next contiguous outbox delivery ordinal for this run."""
    current_max = await conn.fetchval(
        """
        select coalesce(max(delivery_ordinal), 0)
        from analysis_run_outbox_delivery
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    return int(current_max) + 1


async def _append_outbox_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    delivery_ordinal: int,
    delivery_status_code: str,
    occurred_at: datetime,
    valkey_stream_entry_id: str | None = None,
) -> None:
    """Append one claim or delivery event. Stream id is optional."""
    await conn.execute(
        """
        insert into analysis_run_outbox_delivery
            (analysis_run_id, delivery_ordinal, delivery_status_code,
             occurred_at, valkey_stream_entry_id)
        values ($1, $2, $3, $4, $5)
        """,
        analysis_run_id,
        delivery_ordinal,
        delivery_status_code,
        occurred_at,
        valkey_stream_entry_id,
    )


async def _visible_or_404(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Reload the authorized projection or hide the run."""
    started = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if started is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return started


async def _attach_outbox_digest(
    conn: asyncpg.Connection,
    started: dict[str, Any],
) -> dict[str, Any]:
    """Expose the wake-up digest to the start API, never to the client body."""
    digest = await conn.fetchval(
        """
        select request_sha256
        from analysis_run_outbox
        where analysis_run_id = $1
        """,
        started["analysis_run_id"],
    )
    if not digest:
        return started
    attached = dict(started)
    attached["outbox_request_sha256"] = str(digest)
    return attached


async def _lock_start_run(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> asyncpg.Record:
    """Lock the run row used by enqueue and delivery."""
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
    if locked is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return locked


async def enqueue_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Append Running and one outbox row, or resume an undelivered item.

    Period-report is rejected so this path cannot invent a calibrated
    score. A Succeeded retry returns the stored reconstruction. A
    Running row with an undelivered outbox is a crash resume. A Running
    row without pending work is 409. Hidden runs 404.
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

    locked = await _lock_start_run(conn, analysis_run_id)
    locked_status = await conn.fetchval(
        """
        select status_code
        from analysis_run_current_status
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    if locked_status == _SUCCEEDED:
        return await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        )
    if locked_status == _RUNNING:
        latest = await _latest_outbox_delivery(conn, analysis_run_id)
        if latest_outbox_delivery_is_delivered(latest):
            raise AnalysisRunStartError(
                409,
                "Open this run. Start is only for a Pending lineage reconstruction "
                "or TEPP measurement.",
            )
        has_outbox = await conn.fetchval(
            """
            select 1 from analysis_run_outbox where analysis_run_id = $1
            """,
            analysis_run_id,
        )
        if has_outbox is None:
            raise AnalysisRunStartError(
                409,
                "Open this run. Start is only for a Pending lineage reconstruction "
                "or TEPP measurement.",
            )
        return await _attach_outbox_digest(
            conn,
            await _visible_or_404(
                conn, analysis_run_id, account_id, affiliated_entity_ids
            ),
        )
    if locked_status != _PENDING:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )

    now = await conn.fetchval("select clock_timestamp()")
    digest = outbox_request_digest(
        analysis_run_id=str(locked["analysis_run_id"]),
        work_kind_code=str(locked["run_kind_code"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
    )
    try:
        await _append_status(
            conn,
            analysis_run_id,
            await _next_status_ordinal(conn, analysis_run_id),
            _RUNNING,
            now,
        )
        await conn.execute(
            """
            insert into analysis_run_outbox
                (analysis_run_id, work_kind_code, request_sha256, enqueued_at)
            values ($1, $2, $3, $4)
            """,
            analysis_run_id,
            locked["run_kind_code"],
            digest,
            now,
        )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    return await _attach_outbox_digest(
        conn,
        await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        ),
    )


async def deliver_queued_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
    adjudication_client: AdjudicationClient | None = None,
    valkey_stream_entry_id: str | None = None,
) -> dict[str, Any]:
    """Claim the outbox row and finish ThreadWeave or TEPP.

    A delivered row replays the stored result. Missing work is 409.
    TEPP stays Failed when the transport is missing or the envelope is
    not persistable. No theta is invented.
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
    if current["status_code"] == _SUCCEEDED:
        return current

    outbox = await conn.fetchrow(
        """
        select outbox.analysis_run_id, outbox.work_kind_code,
               run.knowledge_cutoff, run.idempotency_key,
               run.analysis_source_snapshot_id, snapshot.snapshot_sha256,
               scope.corporate_entity_id
        from analysis_run_outbox outbox
        join analysis_run run on run.analysis_run_id = outbox.analysis_run_id
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where outbox.analysis_run_id = $1
        for update of outbox
        """,
        analysis_run_id,
    )
    if outbox is None:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )
    latest = await _latest_outbox_delivery(conn, analysis_run_id)
    if latest_outbox_delivery_is_delivered(latest):
        return await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        )
    now = datetime.now(UTC)
    try:
        if not latest_outbox_delivery_is_claimed(latest):
            await _append_outbox_delivery(
                conn,
                analysis_run_id,
                await _next_outbox_delivery_ordinal(conn, analysis_run_id),
                "analysis_outbox_claimed",
                now,
                valkey_stream_entry_id,
            )
        if outbox["work_kind_code"] == _TEPP_KIND:
            await _deliver_tepp_measurement(
                conn,
                analysis_run_id=analysis_run_id,
                locked=outbox,
                tepp_client=tepp_client or TeppClient(),
            )
        elif outbox["work_kind_code"] == _TOPIC_LINEAGE_KIND:
            await _deliver_topic_lineage_measurement(
                conn,
                analysis_run_id=analysis_run_id,
                locked=outbox,
                tepp_client=tepp_client or TeppClient(),
            )
        else:
            await _deliver_lineage_reconstruction(
                conn,
                analysis_run_id=analysis_run_id,
                locked=outbox,
                affiliated_entity_ids=affiliated_entity_ids,
                adjudication_client=adjudication_client,
            )
        finished = datetime.now(UTC)
        finished = max(finished, now)
        await _append_outbox_delivery(
            conn,
            analysis_run_id,
            await _next_outbox_delivery_ordinal(conn, analysis_run_id),
            "analysis_outbox_delivered",
            finished,
            valkey_stream_entry_id,
        )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    return await _visible_or_404(
        conn, analysis_run_id, account_id, affiliated_entity_ids
    )


async def start_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
    adjudication_client: AdjudicationClient | None = None,
    valkey_stream_entry_id: str | None = None,
) -> dict[str, Any]:
    """Enqueue then deliver on one connection.

    The HTTP start path commits the outbox before this delivery so a
    crash leaves Running plus a durable work item. Callers that wrap
    both steps in one transaction keep the older all-or-nothing
    behavior.
    """
    queued = await enqueue_pending_analysis_run(
        conn,
        analysis_run_id=analysis_run_id,
        account_id=account_id,
        affiliated_entity_ids=affiliated_entity_ids,
    )
    if queued["status_code"] == _SUCCEEDED:
        return queued
    return await deliver_queued_analysis_run(
        conn,
        analysis_run_id=analysis_run_id,
        account_id=account_id,
        affiliated_entity_ids=affiliated_entity_ids,
        tepp_client=tepp_client,
        adjudication_client=adjudication_client,
        valkey_stream_entry_id=valkey_stream_entry_id,
    )


async def _deliver_lineage_reconstruction(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    affiliated_entity_ids: list[str],
    adjudication_client: AdjudicationClient | None = None,
) -> None:
    """Persist ThreadWeave parent choices for the frozen bag."""
    now = datetime.now(UTC)
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
    edges = lineage_edge_specs(records_from_source_posts(rows), llm=adjudication_client)
    digest = reconstruction_result_digest(edges)
    finished = datetime.now(UTC)
    finished = max(finished, now)
    await conn.execute(
        """
        insert into analysis_run_reconstruction
            (analysis_run_id, result_sha256, edge_count, reconstructed_at, recorded_at)
        values ($1, $2, $3, clock_timestamp(), clock_timestamp())
        """,
        analysis_run_id,
        digest,
        len(edges),
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
        await _next_status_ordinal(conn, analysis_run_id),
        _SUCCEEDED,
        finished,
    )


async def _deliver_tepp_measurement(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    tepp_client: TeppClient,
) -> None:
    """Submit the frozen snapshot through ``tepp_client``. Never persist a theta."""
    now = datetime.now(UTC)
    request = tepp_run_request(
        idempotency_key=str(locked["idempotency_key"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
        corporate_entity_id=str(locked["corporate_entity_id"]),
    )
    status_code, failure_code, envelope = _tepp_submission(tepp_client, request)
    if status_code == _SUCCEEDED and envelope is not None and not await _persist_tepp_result(
        conn,
        analysis_run_id=analysis_run_id,
        envelope=envelope,
    ):
        status_code = _FAILED
        failure_code = "tepp_result_not_persisted"
    finished = datetime.now(UTC)
    finished = max(finished, now)
    await _append_status(
        conn,
        analysis_run_id,
        await _next_status_ordinal(conn, analysis_run_id),
        status_code,
        finished,
        failure_code,
    )


async def _deliver_topic_lineage_measurement(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    tepp_client: TeppClient,
) -> None:
    """Submit the frozen snapshot through ``tepp_client`` for topic-lineage.

    Mirrors :func:`_deliver_tepp_measurement` (ADR 0022) with the
    topic-lineage model contract (ADR 0132). Never persists a locally
    computed topic identity or CHRONOS/TDT event prediction.
    """
    now = datetime.now(timezone.utc)
    request = topic_lineage_run_request(
        idempotency_key=str(locked["idempotency_key"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
        corporate_entity_id=str(locked["corporate_entity_id"]),
    )
    status_code, failure_code, envelope = _tepp_submission(tepp_client, request)
    if status_code == _SUCCEEDED and envelope is not None:
        if not await _persist_topic_lineage_result(
            conn,
            analysis_run_id=analysis_run_id,
            envelope=envelope,
        ):
            status_code = _FAILED
            failure_code = "tepp_result_not_persisted"
    finished = datetime.now(timezone.utc)
    if finished < now:
        finished = now
    await _append_status(
        conn,
        analysis_run_id,
        await _next_status_ordinal(conn, analysis_run_id),
        status_code,
        finished,
        failure_code,
    )

"""Transactional PostgreSQL repository for normalized analysis-run evidence.

The repository writes only opaque source-profile references, hashes, aggregate
counts, bounded configuration, status transitions, and service identifiers.
It never persists source SQL, DSNs, raw post content, image bytes, or provider
credentials. Any async PostgreSQL connection that implements the small
protocols below can be used; no ORM or file-backed database is involved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence

from lineageweave.analysis_run import (
    AnalysisRunCompletion,
    AnalysisRunConfiguration,
    AnalysisRunRegistration,
    AnalysisRunSummary,
    SourceProfileReference,
    SourceSnapshotEvidence,
)


class AsyncTransaction(Protocol):
    """Async context-manager contract returned by PostgreSQL connections."""

    async def __aenter__(self) -> Any:
        """Enter a database transaction."""

    async def __aexit__(
        self, exc_type: Any, exc: Any, traceback: Any
    ) -> bool | None:
        """Commit on success or roll back on failure."""


class AnalysisRunConnection(Protocol):
    """Minimal async PostgreSQL connection surface used by this repository."""

    def transaction(self) -> AsyncTransaction:
        """Return an async transaction context manager."""

    async def fetchrow(
        self, query: str, *arguments: Any
    ) -> Mapping[str, Any] | None:
        """Execute ``query`` and return at most one row."""

    async def fetch(
        self, query: str, *arguments: Any
    ) -> Sequence[Mapping[str, Any]]:
        """Execute ``query`` and return all rows."""

    async def execute(self, query: str, *arguments: Any) -> str:
        """Execute a statement and return its command tag."""


class AnalysisRunConflict(RuntimeError):
    """An immutable profile, snapshot, or idempotency key was reused differently."""


async def register_analysis_run(
    conn: AnalysisRunConnection,
    *,
    registration: AnalysisRunRegistration,
    profile: SourceProfileReference,
    snapshot: SourceSnapshotEvidence,
    configuration: AnalysisRunConfiguration,
) -> str:
    """Create or idempotently reuse one running analysis record.

    The entire profile → snapshot → run → configuration → event write occurs
    in one transaction. Reusing an immutable key with different evidence
    fails closed instead of silently replacing provenance.
    """

    request_digest = configuration.request_digest(profile, snapshot)
    async with conn.transaction():
        profile_row = await conn.fetchrow(
            """
            insert into analysis_source_profile (
                source_profile_key, profile_revision, source_kind_code,
                query_digest_sha256
            ) values ($1, $2, $3, $4)
            on conflict (source_profile_key, profile_revision) do update
            set source_profile_key = excluded.source_profile_key
            where analysis_source_profile.source_kind_code = excluded.source_kind_code
              and analysis_source_profile.query_digest_sha256 = excluded.query_digest_sha256
            returning source_profile_id
            """,
            profile.profile_key,
            profile.profile_revision,
            profile.source_kind_code,
            profile.query_digest_sha256,
        )
        if profile_row is None:
            raise AnalysisRunConflict(
                "source profile revision already exists with different evidence"
            )

        snapshot_row = await conn.fetchrow(
            """
            insert into analysis_source_snapshot (
                source_profile_id, source_digest_sha256, knowledge_cutoff,
                maximum_available_time, row_count, document_count, thread_count
            ) values ($1, $2, $3, $4, $5, $6, $7)
            on conflict (
                source_profile_id, source_digest_sha256, knowledge_cutoff
            ) do update
            set source_digest_sha256 = excluded.source_digest_sha256
            where analysis_source_snapshot.maximum_available_time =
                    excluded.maximum_available_time
              and analysis_source_snapshot.row_count = excluded.row_count
              and analysis_source_snapshot.document_count = excluded.document_count
              and analysis_source_snapshot.thread_count = excluded.thread_count
            returning source_snapshot_id
            """,
            profile_row["source_profile_id"],
            snapshot.source_digest_sha256,
            snapshot.knowledge_cutoff,
            snapshot.maximum_available_time,
            snapshot.row_count,
            snapshot.document_count,
            snapshot.thread_count,
        )
        if snapshot_row is None:
            raise AnalysisRunConflict(
                "source snapshot already exists with different aggregate evidence"
            )

        run_row = await conn.fetchrow(
            """
            insert into analysis_run_record (
                source_snapshot_id, requested_by_account_id, run_status_code,
                idempotency_key, request_digest_sha256, started_at
            ) values ($1, $2::uuid, 'analysis_run_running', $3, $4, $5)
            on conflict (idempotency_key) do update
            set idempotency_key = excluded.idempotency_key
            where analysis_run_record.request_digest_sha256 =
                    excluded.request_digest_sha256
              and analysis_run_record.requested_by_account_id =
                    excluded.requested_by_account_id
            returning analysis_run_id, started_at
            """,
            snapshot_row["source_snapshot_id"],
            registration.requested_by_account_id,
            registration.idempotency_key,
            request_digest,
            registration.started_at,
        )
        if run_row is None:
            raise AnalysisRunConflict(
                "idempotency key already exists for a different request"
            )

        analysis_run_id = run_row["analysis_run_id"]
        await conn.execute(
            """
            insert into analysis_run_configuration (
                analysis_run_id, row_limit, write_reports, inspect_inline_images,
                validate_runtime_schema, model_contract_version, output_profile
            ) values ($1, $2, $3, $4, $5, $6, $7)
            on conflict (analysis_run_id) do nothing
            """,
            analysis_run_id,
            configuration.row_limit,
            configuration.write_reports,
            configuration.inspect_inline_images,
            configuration.validate_runtime_schema,
            configuration.model_contract_version,
            configuration.output_profile,
        )
        await conn.execute(
            """
            insert into analysis_run_event (
                analysis_run_id, event_type_code, actor_account_id,
                occurred_at, payload_digest_sha256
            ) values ($1, 'analysis_run_started_event', $2::uuid, $3, $4)
            on conflict (
                analysis_run_id, event_type_code, occurred_at,
                payload_digest_sha256
            ) do nothing
            """,
            analysis_run_id,
            registration.requested_by_account_id,
            run_row["started_at"],
            request_digest,
        )
    return str(analysis_run_id)


async def complete_analysis_run(
    conn: AnalysisRunConnection,
    *,
    analysis_run_id: str,
    actor_account_id: str,
    succeeded: bool,
    completed_at: datetime,
) -> None:
    """Complete a running record exactly once and append its audit event."""

    completion = AnalysisRunCompletion(
        analysis_run_id=analysis_run_id,
        actor_account_id=actor_account_id,
        succeeded=succeeded,
        completed_at=completed_at,
    )
    status_code = (
        "analysis_run_succeeded"
        if completion.succeeded
        else "analysis_run_failed"
    )
    event_type_code = (
        "analysis_run_completed_event"
        if completion.succeeded
        else "analysis_run_failed_event"
    )
    async with conn.transaction():
        run_row = await conn.fetchrow(
            """
            update analysis_run_record
            set run_status_code = $2, completed_at = $3
            where analysis_run_id = $1::uuid
              and run_status_code = 'analysis_run_running'
              and completed_at is null
            returning request_digest_sha256
            """,
            completion.analysis_run_id,
            status_code,
            completion.completed_at,
        )
        if run_row is None:
            raise AnalysisRunConflict("analysis run is missing or already completed")
        await conn.execute(
            """
            insert into analysis_run_event (
                analysis_run_id, event_type_code, actor_account_id,
                occurred_at, payload_digest_sha256
            ) values ($1::uuid, $2, $3::uuid, $4, $5)
            """,
            completion.analysis_run_id,
            event_type_code,
            completion.actor_account_id,
            completion.completed_at,
            run_row["request_digest_sha256"],
        )


async def list_analysis_run_summaries(
    conn: AnalysisRunConnection,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return the newest source-redacting run summaries for an admin surface."""

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 100
    ):
        raise ValueError("limit must be an integer from 1 through 100")
    rows = await conn.fetch(
        """
        select
            ar.analysis_run_id,
            asp.source_profile_key,
            asp.profile_revision,
            ar.run_status_code,
            ar.request_digest_sha256,
            ass.source_digest_sha256,
            ass.knowledge_cutoff,
            ass.maximum_available_time,
            ass.row_count,
            ass.document_count,
            ass.thread_count,
            ar.started_at,
            ar.completed_at,
            arc.row_limit,
            arc.write_reports,
            arc.inspect_inline_images,
            arc.validate_runtime_schema,
            arc.model_contract_version,
            arc.output_profile
        from analysis_run_record ar
        join analysis_source_snapshot ass
          on ass.source_snapshot_id = ar.source_snapshot_id
        join analysis_source_profile asp
          on asp.source_profile_id = ass.source_profile_id
        join analysis_run_configuration arc
          on arc.analysis_run_id = ar.analysis_run_id
        order by ar.started_at desc, ar.analysis_run_id desc
        limit $1
        """,
        limit,
    )
    summaries: list[dict[str, Any]] = []
    for row in rows:
        configuration = AnalysisRunConfiguration(
            row_limit=row["row_limit"],
            write_reports=row["write_reports"],
            inspect_inline_images=row["inspect_inline_images"],
            validate_runtime_schema=row["validate_runtime_schema"],
            model_contract_version=row["model_contract_version"],
            output_profile=row["output_profile"],
        )
        summary = AnalysisRunSummary(
            analysis_run_id=str(row["analysis_run_id"]),
            profile_key=row["source_profile_key"],
            profile_revision=row["profile_revision"],
            run_status_code=row["run_status_code"],
            request_digest_sha256=row["request_digest_sha256"],
            source_digest_sha256=row["source_digest_sha256"],
            knowledge_cutoff=row["knowledge_cutoff"],
            maximum_available_time=row["maximum_available_time"],
            row_count=row["row_count"],
            document_count=row["document_count"],
            thread_count=row["thread_count"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            configuration=configuration,
        )
        summaries.append(summary.public_json())
    return summaries

"""Live PostgreSQL proof for per-principal Global Ask active-job admission.

The in-memory queue test exercises call ordering, but an advisory lock is a
PostgreSQL concurrency contract. This test uses two independent database
connections against the migrated schema so a count-then-insert regression cannot
masquerade as serialized admission.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from backend.app.global_ask_queue import (
    GlobalAskOutstandingLimitExceeded,
    enqueue_global_ask_job,
)

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_ACTIVE_ADMISSION_MIGRATION = _MIGRATIONS_DIR / "0246_global_ask_active_admission_index.sql"
_ACTIVE_ADMISSION_ROLLBACK = (
    _MIGRATIONS_DIR / "rollback" / "0246_global_ask_active_admission_index.sql"
)
_ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _run_sql_file(
    database_dsn: str, sql_file: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Execute one production SQL file through the repository's psql boundary."""
    return subprocess.run(
        [
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            database_dsn,
            "-f",
            str(sql_file),
        ],
        check=check,
        capture_output=True,
        text=True,
    )


def _apply_migrations(database_dsn: str) -> None:
    """Replay the production migration stream through psql in filename order."""
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        _run_sql_file(database_dsn, migration)


class _RecordingValkey:
    """Record wake-ups without replacing the PostgreSQL admission boundary."""

    def __init__(self) -> None:
        self.published_job_ids: list[str] = []

    async def xadd(self, _stream: str, fields: dict[str, str], **_kwargs) -> None:
        self.published_job_ids.append(fields["global_ask_job_id"])


async def _connect_admin_or_skip() -> asyncpg.Connection:
    try:
        return await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (OSError, asyncpg.PostgresError) as exc:
        message = f"required PostgreSQL is unreachable: {type(exc).__name__}"
        if os.environ.get("CI") == "true":
            pytest.fail(message)
        pytest.skip(message)


async def _assert_active_admission_index(connection: asyncpg.Connection) -> None:
    """The synchronous principal-cap query must not scan terminal job history."""
    index_row = await connection.fetchrow(
        """
        select pg_get_indexdef(index_relation.oid) as index_definition,
               index_catalog.indisvalid,
               index_catalog.indisready
          from pg_class index_relation
          join pg_index index_catalog
            on index_catalog.indexrelid = index_relation.oid
          join pg_class table_relation
            on table_relation.oid = index_catalog.indrelid
         where table_relation.relname = 'global_ask_job'
           and index_relation.relname = 'global_ask_job_active_account_idx'
        """
    )
    assert index_row is not None
    assert index_row["indisvalid"] is True
    assert index_row["indisready"] is True
    normalized = index_row["index_definition"].lower()
    assert "requesting_account_id" in normalized
    assert "where" in normalized
    assert "queued" in normalized
    assert "running" in normalized


async def _parallel_admission_scenario() -> None:
    database_name = f"lineageweave_ask_admission_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    connections: list[asyncpg.Connection] = []
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations(database_dsn)

        observer = await asyncpg.connect(database_dsn)
        await _assert_active_admission_index(observer)
        await observer.execute(
            """
            insert into user_account
                (user_account_id, external_subject_id, display_name, email_address)
            values ($1::uuid, $2, $3, $4)
            """,
            _ACCOUNT_ID,
            "synthetic-ask-admission",
            "Synthetic Ask Admission",
            "synthetic-ask-admission@example.test",
        )

        connections = [
            await asyncpg.connect(database_dsn),
            await asyncpg.connect(database_dsn),
        ]
        valkey = _RecordingValkey()

        async def submit(conn: asyncpg.Connection) -> str:
            return await enqueue_global_ask_job(
                conn,
                valkey,
                requesting_account_id=_ACCOUNT_ID,
                question_text="What changed?",
                verify_external_requested=False,
                knowledge_cutoff=None,
                corporate_entity_ids=frozenset(),
                process_unit_ids=frozenset(),
                max_outstanding_jobs=1,
            )

        results = await asyncio.gather(
            *(submit(conn) for conn in connections), return_exceptions=True
        )
        accepted = [result for result in results if isinstance(result, str)]
        rejected = [
            result
            for result in results
            if isinstance(result, GlobalAskOutstandingLimitExceeded)
        ]

        assert len(accepted) == 1
        assert len(rejected) == 1
        assert all(
            isinstance(result, (str, GlobalAskOutstandingLimitExceeded))
            for result in results
        )
        outstanding = await observer.fetchval(
            """
            select count(*)
              from global_ask_job
             where requesting_account_id = $1::uuid
               and job_status_code in ('queued', 'running')
            """,
            _ACCOUNT_ID,
        )
        assert outstanding == 1
        assert valkey.published_job_ids == accepted
    finally:
        for connection in connections:
            await connection.close()
        if observer is not None:
            await observer.close()
        try:
            await admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = $1 and pid <> pg_backend_pid()",
                database_name,
            )
            await admin.execute(f'drop database if exists "{database_name}"')
        finally:
            await admin.close()


async def _invalid_concurrent_index_recovery_scenario() -> None:
    """A failed concurrent build must fail closed and have an executable recovery."""
    database_name = f"lineageweave_ask_index_recovery_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            if migration == _ACTIVE_ADMISSION_MIGRATION:
                break
            _run_sql_file(database_dsn, migration)

        observer = await asyncpg.connect(database_dsn)
        await observer.execute(
            """
            insert into user_account
                (user_account_id, external_subject_id, display_name, email_address)
            values ($1::uuid, $2, $3, $4)
            """,
            _ACCOUNT_ID,
            "synthetic-index-recovery",
            "Synthetic Index Recovery",
            "synthetic-index-recovery@example.test",
        )
        await observer.executemany(
            """
            insert into global_ask_job
                (requesting_account_id, question_text, job_status_code)
            values ($1::uuid, $2, 'queued')
            """,
            [
                (_ACCOUNT_ID, "first duplicate principal"),
                (_ACCOUNT_ID, "second duplicate principal"),
            ],
        )

        failed_build = subprocess.run(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                database_dsn,
                "-c",
                "create unique index concurrently global_ask_job_active_account_idx "
                "on global_ask_job (requesting_account_id) "
                "where job_status_code in ('queued', 'running')",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert failed_build.returncode != 0
        invalid = await observer.fetchrow(
            """
            select index_catalog.indisvalid, index_catalog.indisready
              from pg_class index_relation
              join pg_index index_catalog
                on index_catalog.indexrelid = index_relation.oid
             where index_relation.relname = 'global_ask_job_active_account_idx'
            """
        )
        assert invalid is not None
        assert invalid["indisvalid"] is False

        retry = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION, check=False)
        assert retry.returncode != 0
        assert "invalid" in (retry.stdout + retry.stderr).lower()

        _run_sql_file(database_dsn, _ACTIVE_ADMISSION_ROLLBACK)
        _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION)
        await _assert_active_admission_index(observer)
    finally:
        if observer is not None:
            await observer.close()
        try:
            await admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = $1 and pid <> pg_backend_pid()",
                database_name,
            )
            await admin.execute(f'drop database if exists "{database_name}"')
        finally:
            await admin.close()


def test_parallel_postgresql_admission_never_overshoots_one_active_job() -> None:
    """Two real sessions for one principal admit exactly one active Ask job."""
    asyncio.run(_parallel_admission_scenario())


def test_failed_concurrent_index_build_has_fail_closed_recovery() -> None:
    """Migration replay must not silently retain an INVALID capacity index."""
    asyncio.run(_invalid_concurrent_index_recovery_scenario())


def test_postgresql_connection_failure_is_fatal_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI must not pass by skipping the PostgreSQL concurrency proof."""

    async def refuse_connection(*_args, **_kwargs):
        raise OSError("synthetic unavailable database")

    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(asyncpg, "connect", refuse_connection)

    with pytest.raises(pytest.fail.Exception, match="required PostgreSQL is unreachable"):
        asyncio.run(_connect_admin_or_skip())

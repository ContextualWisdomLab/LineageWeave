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
_ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _apply_migrations(database_dsn: str) -> None:
    """Replay the production migration stream through psql in filename order."""
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        subprocess.run(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                database_dsn,
                "-f",
                str(migration),
            ],
            check=True,
            capture_output=True,
            text=True,
        )


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
    index_definition = await connection.fetchval(
        """
        select indexdef
          from pg_indexes
         where schemaname = 'public'
           and tablename = 'global_ask_job'
           and indexname = 'global_ask_job_active_account_idx'
        """
    )
    assert index_definition is not None
    normalized = index_definition.lower()
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


def test_parallel_postgresql_admission_never_overshoots_one_active_job() -> None:
    """Two real sessions for one principal admit exactly one active Ask job."""
    asyncio.run(_parallel_admission_scenario())


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

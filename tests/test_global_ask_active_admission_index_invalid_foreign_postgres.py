"""Recovery-guidance regression for foreign invalid admission indexes."""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest


_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_MIGRATION = _MIGRATIONS_DIR / "0251_global_ask_active_admission_index.sql"
_INDEX_NAME = "global_ask_job_active_account_idx"


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _run_sql_file(
    database_dsn: str, sql_file: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", database_dsn, "-f", str(sql_file)],
        check=check,
        capture_output=True,
        text=True,
    )


async def _connect_admin_or_skip() -> asyncpg.Connection:
    try:
        return await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (OSError, asyncpg.PostgresError) as exc:
        message = f"required PostgreSQL is unreachable: {type(exc).__name__}"
        if os.environ.get("CI") == "true":
            pytest.fail(message)
        pytest.skip(message)


def _apply_migrations_before_0251(database_dsn: str) -> None:
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        if migration == _MIGRATION:
            break
        _run_sql_file(database_dsn, migration)


async def _drop_database(admin: asyncpg.Connection, database_name: str) -> None:
    await admin.execute(
        "select pg_terminate_backend(pid) from pg_stat_activity "
        "where datname = $1 and pid <> pg_backend_pid()",
        database_name,
    )
    await admin.execute(f'drop database if exists "{database_name}"')


async def _foreign_invalid_index_scenario() -> None:
    database_name = f"lineageweave_ask_index_foreign_invalid_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    duplicate_account_id = uuid.uuid4()
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_0251(database_dsn)
        observer = await asyncpg.connect(database_dsn)

        await observer.execute(
            """
            create table global_ask_job_shadow (
                requesting_account_id uuid not null,
                job_status_code text not null
            )
            """
        )
        await observer.executemany(
            "insert into global_ask_job_shadow(requesting_account_id, job_status_code) "
            "values($1, 'queued')",
            [(duplicate_account_id,), (duplicate_account_id,)],
        )
        with pytest.raises(asyncpg.PostgresError):
            await observer.execute(
                f"create unique index concurrently {_INDEX_NAME} "
                "on global_ask_job_shadow(requesting_account_id)"
            )

        invalid = await observer.fetchval(
            "select not indisvalid from pg_index "
            f"where indexrelid = 'public.{_INDEX_NAME}'::regclass"
        )
        assert invalid is True, "fixture must leave PostgreSQL's failed concurrent index"

        attempt = _run_sql_file(database_dsn, _MIGRATION, check=False)
        output = (attempt.stdout + attempt.stderr).lower()
        assert attempt.returncode != 0
        assert "incompatible" in output
        assert "rollback/0251_global_ask_active_admission_index.sql" not in output

        indexed_table = await observer.fetchval(
            "select indrelid::regclass::text from pg_index "
            f"where indexrelid = 'public.{_INDEX_NAME}'::regclass"
        )
        assert indexed_table == "global_ask_job_shadow"
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


def test_foreign_invalid_index_does_not_prescribe_repository_rollback() -> None:
    """Failed foreign DDL must not be mistaken for migration-owned recovery."""
    asyncio.run(_foreign_invalid_index_scenario())

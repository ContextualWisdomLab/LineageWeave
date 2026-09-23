"""PostgreSQL rollback ownership guard for the Global Ask admission index."""

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
_ACTIVE_ADMISSION_MIGRATION = _MIGRATIONS_DIR / "0251_global_ask_active_admission_index.sql"
_ACTIVE_ADMISSION_ROLLBACK = (
    _MIGRATIONS_DIR / "rollback" / "0251_global_ask_active_admission_index.sql"
)


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _run_sql_file(
    database_dsn: str, sql_file: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
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


async def _connect_admin_or_skip() -> asyncpg.Connection:
    try:
        return await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (OSError, asyncpg.PostgresError) as exc:
        message = f"required PostgreSQL is unreachable: {type(exc).__name__}"
        if os.environ.get("CI") == "true":
            pytest.fail(message)
        pytest.skip(message)


def _apply_migrations_before_active_admission(database_dsn: str) -> None:
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        if migration == _ACTIVE_ADMISSION_MIGRATION:
            break
        _run_sql_file(database_dsn, migration)


async def _drop_database(admin: asyncpg.Connection, database_name: str) -> None:
    await admin.execute(
        "select pg_terminate_backend(pid) from pg_stat_activity "
        "where datname = $1 and pid <> pg_backend_pid()",
        database_name,
    )
    await admin.execute(f'drop database if exists "{database_name}"')


async def _rollback_preserves_unowned_valid_index_scenario() -> None:
    database_name = f"lineageweave_ask_rollback_owner_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_active_admission(database_dsn)

        observer = await asyncpg.connect(database_dsn)
        await observer.execute(
            """
            create index global_ask_job_active_account_idx
                on public.global_ask_job (requesting_account_id)
                where job_status_code in ('queued', 'running')
            """
        )
        marker = await observer.fetchval(
            "select obj_description('public.global_ask_job_active_account_idx'::regclass, 'pg_class')"
        )
        assert marker is None

        rollback = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_ROLLBACK, check=False)
        output = (rollback.stdout + rollback.stderr).lower()
        assert rollback.returncode != 0
        assert "not repository-owned" in output

        retained = await observer.fetchrow(
            """
            select index_catalog.indisvalid,
                   index_catalog.indisready,
                   obj_description(index_catalog.indexrelid, 'pg_class') as marker
              from pg_index index_catalog
             where index_catalog.indexrelid =
                   'public.global_ask_job_active_account_idx'::regclass
            """
        )
        assert retained is not None
        assert retained["indisvalid"] is True
        assert retained["indisready"] is True
        assert retained["marker"] is None
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


def test_rollback_refuses_valid_unowned_same_named_index() -> None:
    """Rollback must not delete a valid index that lacks repository ownership."""
    asyncio.run(_rollback_preserves_unowned_valid_index_scenario())


def test_rollback_validation_and_drop_share_one_locked_transaction() -> None:
    """Ownership validation and destructive DROP must not have a replacement race."""
    normalized = " ".join(_ACTIVE_ADMISSION_ROLLBACK.read_text().lower().split())
    begin_position = normalized.find("begin;")
    lock_position = normalized.find(
        "lock table public.global_ask_job in access exclusive mode;"
    )
    validation_position = normalized.find("do $$")
    drop_position = normalized.find(
        "drop index if exists public.global_ask_job_active_account_idx;"
    )
    commit_position = normalized.rfind("commit;")

    assert min(
        begin_position,
        lock_position,
        validation_position,
        drop_position,
        commit_position,
    ) >= 0
    assert (
        begin_position
        < lock_position
        < validation_position
        < drop_position
        < commit_position
    )
    assert "drop index concurrently" not in normalized

"""PostgreSQL recovery guard for the Global Ask active-admission index."""

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
_INDEX_CONTRACT = "lineageweave/global-ask-active-admission-index/v1"


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


def _run_sql_file_after_commands(
    database_dsn: str,
    commands: tuple[str, ...],
    sql_file: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = ["psql", "-X", "-v", "ON_ERROR_STOP=1", database_dsn]
    for sql in commands:
        command.extend(("-c", sql))
    command.extend(("-f", str(sql_file)))
    return subprocess.run(
        command,
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


async def _shadow_index_scenario() -> None:
    database_name = f"lineageweave_ask_index_shadow_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_active_admission(database_dsn)

        observer = await asyncpg.connect(database_dsn)
        await observer.execute(
            """
            create table global_ask_job_shadow (
                requesting_account_id uuid not null,
                job_status_code text not null
            )
            """
        )
        await observer.execute(
            """
            create index global_ask_job_active_account_idx
                on global_ask_job_shadow (requesting_account_id)
                where job_status_code in ('queued', 'running')
            """
        )

        retry = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION, check=False)
        output = (retry.stdout + retry.stderr).lower()
        assert retry.returncode != 0
        assert "incompatible" in output
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


async def _same_table_narrow_predicate_scenario() -> None:
    database_name = f"lineageweave_ask_index_predicate_{uuid.uuid4().hex[:12]}"
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
                on global_ask_job (requesting_account_id)
                where job_status_code in ('queued', 'running') and false
            """
        )
        await observer.execute(
            "comment on index global_ask_job_active_account_idx is $1",
            _INDEX_CONTRACT,
        )

        retry = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION, check=False)
        output = (retry.stdout + retry.stderr).lower()
        assert retry.returncode != 0
        assert "incompatible" in output
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


async def _same_table_unfiltered_index_scenario() -> None:
    database_name = f"lineageweave_ask_index_unfiltered_{uuid.uuid4().hex[:12]}"
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
                on global_ask_job (requesting_account_id)
            """
        )
        await observer.execute(
            "comment on index global_ask_job_active_account_idx is $1",
            _INDEX_CONTRACT,
        )

        retry = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION, check=False)
        output = (retry.stdout + retry.stderr).lower()
        assert retry.returncode != 0
        assert "incompatible" in output
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


async def _temporary_table_shadow_scenario() -> None:
    database_name = f"lineageweave_ask_index_temp_shadow_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_active_admission(database_dsn)

        attempt = _run_sql_file_after_commands(
            database_dsn,
            (
                "create temporary table global_ask_job (requesting_account_id uuid not null, job_status_code text not null) on commit preserve rows",
                "set search_path = pg_temp, public",
            ),
            _ACTIVE_ADMISSION_MIGRATION,
            check=False,
        )
        assert attempt.returncode == 0, attempt.stdout + attempt.stderr

        observer = await asyncpg.connect(database_dsn)
        public_index = await observer.fetchval(
            "select to_regclass('public.global_ask_job_active_account_idx')::text"
        )
        assert public_index == "global_ask_job_active_account_idx"
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


async def _rollback_temp_index_shadow_scenario() -> None:
    database_name = f"lineageweave_ask_index_rollback_shadow_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_active_admission(database_dsn)
        _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION)

        rollback = _run_sql_file_after_commands(
            database_dsn,
            (
                "create temporary table global_ask_job (requesting_account_id uuid not null, job_status_code text not null) on commit preserve rows",
                "create index global_ask_job_active_account_idx on global_ask_job (requesting_account_id)",
                "set search_path = pg_temp, public",
            ),
            _ACTIVE_ADMISSION_ROLLBACK,
            check=False,
        )
        assert rollback.returncode == 0, rollback.stdout + rollback.stderr

        observer = await asyncpg.connect(database_dsn)
        public_index = await observer.fetchval(
            "select to_regclass('public.global_ask_job_active_account_idx')::text"
        )
        assert public_index is None
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


async def _canonical_index_replay_scenario() -> None:
    database_name = f"lineageweave_ask_index_replay_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_active_admission(database_dsn)
        _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION)

        observer = await asyncpg.connect(database_dsn)
        contract = await observer.fetchval(
            "select obj_description('public.global_ask_job_active_account_idx'::regclass, 'pg_class')"
        )
        assert contract == _INDEX_CONTRACT

        replay = _run_sql_file(database_dsn, _ACTIVE_ADMISSION_MIGRATION, check=False)
        assert replay.returncode == 0, replay.stdout + replay.stderr
    finally:
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


def test_same_named_index_on_shadow_table_fails_closed() -> None:
    """A same-named index on another table must never satisfy migration 0251."""
    asyncio.run(_shadow_index_scenario())


def test_same_table_index_with_narrower_predicate_fails_closed() -> None:
    """A version-marked lookalike that cannot serve all active rows must fail."""
    asyncio.run(_same_table_narrow_predicate_scenario())


def test_same_table_unfiltered_index_fails_closed() -> None:
    """A version-marked non-partial index must not bypass predicate validation."""
    asyncio.run(_same_table_unfiltered_index_scenario())


def test_temporary_table_shadow_cannot_capture_forward_migration() -> None:
    """Search-path shadowing must not divert migration 0251 into pg_temp."""
    asyncio.run(_temporary_table_shadow_scenario())


def test_temporary_index_shadow_cannot_capture_rollback() -> None:
    """Recovery must drop the public index even when pg_temp shadows its name."""
    asyncio.run(_rollback_temp_index_shadow_scenario())


def test_canonical_index_contract_survives_replay() -> None:
    """The repository-owned index identity must be versioned and replay-safe."""
    asyncio.run(_canonical_index_replay_scenario())

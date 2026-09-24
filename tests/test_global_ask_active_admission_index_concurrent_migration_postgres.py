"""Concurrent migration regression for the Global Ask admission index."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest


_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _ROOT / "migrations"
_MIGRATION = _MIGRATIONS_DIR / "0251_global_ask_active_admission_index.sql"
_INDEX_NAME = "global_ask_job_active_account_idx"
_INDEX_CONTRACT = "lineageweave/global-ask-active-admission-index/v1"
_BUSY_MESSAGE = "migration 0251 is already running"


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


async def _concurrent_migration_scenario() -> None:
    database_name = f"lineageweave_ask_index_concurrent_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    temporary_path: Path | None = None
    first: subprocess.Popen[str] | None = None
    second: subprocess.Popen[str] | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_0251(database_dsn)
        observer = await asyncpg.connect(database_dsn)

        source = _MIGRATION.read_text(encoding="utf-8")
        marker = "-- Conditional DDL starts here."
        assert marker in source, "concurrency fixture must intercept post-preflight DDL"
        delayed = source.replace(marker, "select pg_sleep(3);\n\n" + marker, 1)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", encoding="utf-8", delete=False
        ) as handle:
            handle.write(delayed)
            temporary_path = Path(handle.name)

        first = subprocess.Popen(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                database_dsn,
                "-f",
                str(temporary_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            sleeping = await observer.fetchval(
                "select exists (select 1 from pg_stat_activity "
                "where datname = $1 and state = 'active' and query ilike '%pg_sleep(3)%')",
                database_name,
            )
            if sleeping:
                break
            await asyncio.sleep(0.05)
        else:
            raise AssertionError("0251 concurrency barrier was not observed")

        second_started = time.monotonic()
        second = subprocess.Popen(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                database_dsn,
                "-f",
                str(_MIGRATION),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        second_stdout, second_stderr = second.communicate(timeout=2)
        second_elapsed = time.monotonic() - second_started
        assert second.returncode != 0, second_stdout + second_stderr
        assert second_elapsed < 2
        assert _BUSY_MESSAGE in (second_stdout + second_stderr).lower()

        first_stdout, first_stderr = first.communicate(timeout=12)
        assert first.returncode == 0, first_stdout + first_stderr

        retry = _run_sql_file(database_dsn, _MIGRATION, check=False)
        assert retry.returncode == 0, retry.stdout + retry.stderr

        index_count = await observer.fetchval(
            "select count(*) from pg_class where oid = to_regclass($1)",
            f"public.{_INDEX_NAME}",
        )
        assert index_count == 1
        contract = await observer.fetchval(
            f"select obj_description('public.{_INDEX_NAME}'::regclass, 'pg_class')"
        )
        assert contract == _INDEX_CONTRACT
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if observer is not None:
            await observer.close()
        try:
            await _drop_database(admin, database_name)
        finally:
            await admin.close()


def test_concurrent_repository_migration_fails_fast_then_replays() -> None:
    """A competing 0251 runner must fail promptly and become replay-safe."""
    asyncio.run(_concurrent_migration_scenario())

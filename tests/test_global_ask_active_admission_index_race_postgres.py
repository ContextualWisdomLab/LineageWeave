"""Race regressions for ownership-safe Global Ask admission-index migration."""

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


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _run_sql_file(database_dsn: str, sql_file: Path) -> None:
    subprocess.run(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", database_dsn, "-f", str(sql_file)],
        check=True,
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


def _migration_source_with_sleep_before(marker: str) -> str:
    source = _MIGRATION.read_text(encoding="utf-8")
    assert marker in source, f"race fixture must intercept {marker!r}"
    return source.replace(marker, "select pg_sleep(3);\n" + marker, 1)


def _start_migration_source(
    database_dsn: str, source: str
) -> tuple[subprocess.Popen[str], Path]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", encoding="utf-8", delete=False
    ) as handle:
        handle.write(source)
        temporary_path = Path(handle.name)

    process = subprocess.Popen(
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
    return process, temporary_path


async def _wait_for_race_barrier(observer: asyncpg.Connection, database_name: str) -> None:
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        sleeping = await observer.fetchval(
            "select exists (select 1 from pg_stat_activity "
            "where datname = $1 and state = 'active' and query ilike '%pg_sleep(3)%')",
            database_name,
        )
        if sleeping:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("0251 race barrier was not observed")


async def _replace_with_narrow_foreign_index(observer: asyncpg.Connection) -> None:
    await observer.execute(f"drop index public.{_INDEX_NAME}")
    await observer.execute(
        f"""
        create index {_INDEX_NAME}
            on global_ask_job (requesting_account_id)
            where job_status_code in ('queued', 'running') and false
        """
    )


async def _assert_foreign_index_remains_unowned(observer: asyncpg.Connection) -> None:
    ownership = await observer.fetchval(
        f"select obj_description('public.{_INDEX_NAME}'::regclass, 'pg_class')"
    )
    assert ownership is None, "migration must never stamp ownership onto a raced foreign index"
    predicate = await observer.fetchval(
        f"select pg_get_expr(indpred, indrelid, true) from pg_index "
        f"where indexrelid = 'public.{_INDEX_NAME}'::regclass"
    )
    assert predicate is not None and "false" in predicate.lower()


async def _absent_name_race_scenario() -> None:
    database_name = f"lineageweave_ask_index_race_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    temporary_path: Path | None = None
    process: subprocess.Popen[str] | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_0251(database_dsn)
        observer = await asyncpg.connect(database_dsn)

        source = _migration_source_with_sleep_before("-- Conditional DDL starts here.")
        process, temporary_path = _start_migration_source(database_dsn, source)
        await _wait_for_race_barrier(observer, database_name)

        await observer.execute(
            f"""
            create index {_INDEX_NAME}
                on global_ask_job (requesting_account_id)
                where job_status_code in ('queued', 'running') and false
            """
        )

        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode != 0, stdout + stderr
        await _assert_foreign_index_remains_unowned(observer)
    finally:
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


async def _replay_swap_scenario() -> None:
    database_name = f"lineageweave_ask_index_replay_race_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    temporary_path: Path | None = None
    process: subprocess.Popen[str] | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_0251(database_dsn)
        _run_sql_file(database_dsn, _MIGRATION)
        observer = await asyncpg.connect(database_dsn)

        source = _migration_source_with_sleep_before("-- Conditional DDL starts here.")
        process, temporary_path = _start_migration_source(database_dsn, source)
        await _wait_for_race_barrier(observer, database_name)

        await _replace_with_narrow_foreign_index(observer)

        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode != 0, stdout + stderr
        await _assert_foreign_index_remains_unowned(observer)
    finally:
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


async def _created_index_swap_before_oid_capture_scenario() -> None:
    database_name = f"lineageweave_ask_index_created_race_{uuid.uuid4().hex[:12]}"
    database_dsn = _database_dsn(database_name)
    admin = await _connect_admin_or_skip()
    observer: asyncpg.Connection | None = None
    temporary_path: Path | None = None
    process: subprocess.Popen[str] | None = None
    try:
        await admin.execute(f'create database "{database_name}"')
        _apply_migrations_before_0251(database_dsn)
        observer = await asyncpg.connect(database_dsn)

        source = _migration_source_with_sleep_before(
            "select 'public.global_ask_job_active_account_idx'::regclass::oid"
        )
        process, temporary_path = _start_migration_source(database_dsn, source)
        await _wait_for_race_barrier(observer, database_name)

        await _replace_with_narrow_foreign_index(observer)

        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode != 0, stdout + stderr
        await _assert_foreign_index_remains_unowned(observer)
    finally:
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


def test_concurrent_same_name_creation_cannot_steal_repository_ownership() -> None:
    """A relation appearing after absent-name preflight must fail before ownership is stamped."""
    asyncio.run(_absent_name_race_scenario())


def test_replay_cannot_stamp_ownership_after_the_validated_index_is_swapped() -> None:
    """Replay must bind publication to the exact index object validated during preflight."""
    asyncio.run(_replay_swap_scenario())


def test_created_index_swap_is_revalidated_before_ownership_publication() -> None:
    """A post-CREATE replacement must satisfy the canonical shape before publication."""
    asyncio.run(_created_index_swap_before_oid_capture_scenario())

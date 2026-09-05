"""Rollback contract for the versioned UI translation-ledger migration."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest


ROOT = Path(__file__).resolve().parents[1]
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_INITIAL_SCHEMA = ROOT / "migrations" / "0001_initial_schema.sql"
_MEMBER_LOCALE_MIGRATION = ROOT / "migrations" / "0044_member_locale_preference.sql"
_TRANSLATION_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_TRANSLATION_LEDGER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0246_ui_translation_ledger.sql"
)


def test_translation_ledger_migration_has_executable_rollback_contract() -> None:
    """A deployable schema foundation must carry its dependency-safe recovery path."""
    assert _TRANSLATION_LEDGER_ROLLBACK.is_file()
    sql = _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8").lower()

    for fragment in (
        "drop table if exists ui_translation_text",
        "drop table if exists ui_translation_key",
        "drop table if exists ui_translation_resource",
        "drop function if exists guard_ui_translation_child_mutation()",
        "drop function if exists guard_ui_translation_resource_mutation()",
        "add constraint user_account_preferred_locale_ck",
        "'en', 'ko', 'zh', 'ja', 'vi'",
        "from ui_translation_resource",
        "refusing 0246 rollback because translation resources exist",
    ):
        assert fragment in sql

    for unsupported_pre0246_locale in ("'es'", "'de'", "'fr'"):
        assert unsupported_pre0246_locale not in sql


async def _postgres_available_async() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    """Probe PostgreSQL once during collection without adding a sync DB driver."""
    return asyncio.run(_postgres_available_async())


async def _wait_for_user_account_ddl_waiter(connection: asyncpg.Connection) -> None:
    """Wait until rollback has passed its guard and is blocked on user_account DDL."""
    for _ in range(100):
        waiting = await connection.fetchval(
            """
            select exists (
                select 1
                  from pg_locks as lock_state
                  join pg_class as relation
                    on relation.oid = lock_state.relation
                  join pg_namespace as namespace
                    on namespace.oid = relation.relnamespace
                 where namespace.nspname = 'public'
                   and relation.relname = 'user_account'
                   and lock_state.mode = 'AccessExclusiveLock'
                   and not lock_state.granted
            )
            """
        )
        if waiting:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("rollback never reached the user_account DDL wait point")


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_restores_pre0246_schema_projection() -> None:
    """Apply 0246 then rollback and recover the five-locale member projection."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_{uuid.uuid4().hex[:12]}"
        admin_connection = await asyncpg.connect(_ADMIN_DSN)
        await admin_connection.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        try:
            connection = await asyncpg.connect(database_dsn)
            try:
                await connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                await connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
                await connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
                await connection.execute(_TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8"))

                for relation in (
                    "ui_translation_text",
                    "ui_translation_key",
                    "ui_translation_resource",
                ):
                    assert await connection.fetchval("select to_regclass($1)", relation) is None

                constraint_definition = await connection.fetchval(
                    """
                    select pg_get_constraintdef(oid)
                      from pg_constraint
                     where conname = 'user_account_preferred_locale_ck'
                    """
                )
                assert constraint_definition is not None
                for locale in ("en", "ko", "zh", "ja", "vi"):
                    assert f"'{locale}'" in constraint_definition
                for locale in ("es", "de", "fr"):
                    assert f"'{locale}'" not in constraint_definition
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_is_replay_safe_after_success() -> None:
    """Retrying an already-completed empty-foundation rollback must converge cleanly."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_replay_{uuid.uuid4().hex[:12]}"
        admin_connection = await asyncpg.connect(_ADMIN_DSN)
        await admin_connection.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        try:
            connection = await asyncpg.connect(database_dsn)
            try:
                await connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                await connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
                await connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
                rollback_sql = _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8")
                await connection.execute(rollback_sql)
                await connection.execute(rollback_sql)

                assert await connection.fetchval(
                    "select to_regclass('ui_translation_resource')"
                ) is None
                constraint_definition = await connection.fetchval(
                    """
                    select pg_get_constraintdef(oid)
                      from pg_constraint
                     where conname = 'user_account_preferred_locale_ck'
                    """
                )
                assert constraint_definition is not None
                for locale in ("en", "ko", "zh", "ja", "vi"):
                    assert f"'{locale}'" in constraint_definition
                for locale in ("es", "de", "fr"):
                    assert f"'{locale}'" not in constraint_definition
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_refuses_existing_translation_data() -> None:
    """Recovery must not erase draft or published customer copy contrary to ADR 0362."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_guard_{uuid.uuid4().hex[:12]}"
        admin_connection = await asyncpg.connect(_ADMIN_DSN)
        await admin_connection.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        try:
            connection = await asyncpg.connect(database_dsn)
            try:
                await connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                await connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
                await connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
                await connection.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values ('lineageweave', 'customer-master', 1)
                    """
                )

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refusing 0246 rollback because translation resources exist",
                ):
                    await connection.execute(
                        _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8")
                    )
                await connection.execute("rollback")

                assert (
                    await connection.fetchval(
                        "select to_regclass('ui_translation_resource')::text"
                    )
                    == "ui_translation_resource"
                )
                assert await connection.fetchval(
                    "select count(*) from ui_translation_resource"
                ) == 1
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_serializes_empty_guard_against_concurrent_insert() -> None:
    """A resource created after the empty check must never be dropped by rollback."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_race_{uuid.uuid4().hex[:12]}"
        admin_connection = await asyncpg.connect(_ADMIN_DSN)
        await admin_connection.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        blocker: asyncpg.Connection | None = None
        rollback_connection: asyncpg.Connection | None = None
        insert_connection: asyncpg.Connection | None = None
        observer: asyncpg.Connection | None = None
        rollback_task: asyncio.Task[str] | None = None
        insert_task: asyncio.Task[str] | None = None

        try:
            setup_connection = await asyncpg.connect(database_dsn)
            try:
                await setup_connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                await setup_connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
                await setup_connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            finally:
                await setup_connection.close()

            blocker = await asyncpg.connect(database_dsn)
            rollback_connection = await asyncpg.connect(database_dsn)
            insert_connection = await asyncpg.connect(database_dsn)
            observer = await asyncpg.connect(database_dsn)

            await blocker.execute("begin")
            await blocker.execute("lock table user_account in access share mode")

            rollback_task = asyncio.create_task(
                rollback_connection.execute(_TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8"))
            )
            await _wait_for_user_account_ddl_waiter(observer)

            insert_task = asyncio.create_task(
                insert_connection.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values ('lineageweave', 'customer-master', 1)
                    """
                )
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(insert_task), timeout=0.2)

            await blocker.execute("commit")
            await rollback_task
            with pytest.raises(asyncpg.PostgresError):
                _ = await insert_task

            assert await observer.fetchval("select to_regclass('ui_translation_resource')") is None
        finally:
            if blocker is not None and not blocker.is_closed():
                try:
                    await blocker.execute("rollback")
                except asyncpg.PostgresError:
                    # Teardown is best-effort after PostgreSQL ended the transaction.
                    pass
            for task in (rollback_task, insert_task):
                if task is not None and not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, asyncpg.PostgresError):
                        # Cancellation or a terminated transaction is expected in teardown.
                        pass
            for connection in (observer, insert_connection, rollback_connection, blocker):
                if connection is not None and not connection.is_closed():
                    await connection.close()
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

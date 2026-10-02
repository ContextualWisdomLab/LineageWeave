"""Concurrency regression for seed-owner replay versus ordinary root deletion."""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import suppress
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
_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_TRUNCATE_GUARD_MIGRATION = ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql"
_SEED_OWNERSHIP_MIGRATION = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_SEED_OWNERSHIP_TRUNCATE_GUARD = (
    ROOT / "migrations" / "0247_za_ui_translation_seed_ownership_truncate_guard.sql"
)
_SEED_REPLAY_GUARD = (
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql"
)
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_CUSTOMER_MASTER_SEED_FILE = "0248_customer_master_translation_draft.sql"


async def _postgres_available_async() -> bool:
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    return asyncio.run(_postgres_available_async())


async def _wait_until_lock_wait(
    observer: asyncpg.Connection, contender_pid: int
) -> None:
    """Wait until a contender is blocked on a PostgreSQL heavyweight lock."""
    for _ in range(200):
        waiting = await observer.fetchval(
            """
            select wait_event_type = 'Lock'
              from pg_stat_activity
             where pid = $1
            """,
            contender_pid,
        )
        if waiting:
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"backend {contender_pid} never reached the expected lock wait")


async def _apply_migration(
    connection: asyncpg.Connection, migration: Path
) -> None:
    await connection.execute(
        "select set_config('lineageweave.migration_file', $1, false)",
        migration.name,
    )
    await connection.execute(migration.read_text(encoding="utf-8"))


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_seed_owner_replay_and_owned_root_delete_have_one_lock_order() -> None:
    """Replay must not lock ownership then root against delete's root-then-owner path."""

    async def scenario() -> None:
        database_name = f"lineageweave_seed_delete_race_{uuid.uuid4().hex[:12]}"
        admin = await asyncpg.connect(_ADMIN_DSN)
        await admin.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        setup: asyncpg.Connection | None = None
        ownership_holder: asyncpg.Connection | None = None
        replay: asyncpg.Connection | None = None
        deleter: asyncpg.Connection | None = None
        observer: asyncpg.Connection | None = None
        replay_task: asyncio.Task[str] | None = None
        delete_task: asyncio.Task[None] | None = None
        try:
            setup = await asyncpg.connect(database_dsn)
            for migration in (
                _INITIAL_SCHEMA,
                _MEMBER_LOCALE_MIGRATION,
                _LEDGER_MIGRATION,
                _TRUNCATE_GUARD_MIGRATION,
                _SEED_OWNERSHIP_MIGRATION,
                _SEED_OWNERSHIP_TRUNCATE_GUARD,
                _SEED_REPLAY_GUARD,
            ):
                await _apply_migration(setup, migration)
            await setup.execute(
                "select set_config('lineageweave.migration_file', $1, false)",
                _CUSTOMER_MASTER_SEED_FILE,
            )
            await setup.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))

            resource_id = await setup.fetchval(
                """
                select resource_id
                  from public.ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'customer-master'
                   and resource_version = 1
                """
            )
            assert resource_id is not None
            assert (
                await setup.fetchval(
                    """
                    select ownership_state
                      from public.ui_translation_seed_ownership
                     where migration_key = '0248_customer_master_translation_draft'
                    """
                )
                == "owned"
            )

            ownership_holder = await asyncpg.connect(database_dsn)
            replay = await asyncpg.connect(database_dsn)
            deleter = await asyncpg.connect(database_dsn)
            observer = await asyncpg.connect(database_dsn)

            await ownership_holder.execute("begin")
            await ownership_holder.fetchval(
                """
                select 1
                  from public.ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                 for update
                """
            )

            ownership_sql = _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
            replay_task = asyncio.create_task(replay.execute(ownership_sql))
            await _wait_until_lock_wait(observer, replay.get_server_pid())

            async def delete_owned_root() -> None:
                assert deleter is not None
                await deleter.execute("begin")
                try:
                    await deleter.execute(
                        "delete from public.ui_translation_resource where resource_id = $1",
                        resource_id,
                    )
                except Exception:
                    await deleter.execute("rollback")
                    raise
                else:
                    await deleter.execute("commit")

            delete_task = asyncio.create_task(delete_owned_root())
            await _wait_until_lock_wait(observer, deleter.get_server_pid())

            await ownership_holder.execute("commit")
            results = await asyncio.wait_for(
                asyncio.gather(replay_task, delete_task, return_exceptions=True),
                timeout=5,
            )
            assert all(not isinstance(result, Exception) for result in results), results

            assert (
                await setup.fetchval(
                    """
                    select count(*)
                      from public.ui_translation_resource
                     where resource_id = $1
                    """,
                    resource_id,
                )
                == 0
            )
            receipt = await setup.fetchrow(
                """
                select ownership_state, resource_id
                  from public.ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            assert receipt is not None
            assert receipt["ownership_state"] == "retired"
            assert receipt["resource_id"] is None
        finally:
            for task in (delete_task, replay_task):
                if task is not None and not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError, asyncpg.PostgresError):
                        await task
            for connection in (observer, deleter, replay, ownership_holder, setup):
                if connection is not None and not connection.is_closed():
                    with suppress(asyncpg.PostgresError):
                        await connection.execute("rollback")
                    await connection.close()
            await admin.execute(f'drop database "{database_name}"')
            await admin.close()

    asyncio.run(scenario())

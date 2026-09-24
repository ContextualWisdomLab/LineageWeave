"""Concurrency regression for Similar VOC seed replay versus ordinary deletion."""

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
_BASE_MIGRATIONS = (
    ROOT / "migrations" / "0001_initial_schema.sql",
    ROOT / "migrations" / "0044_member_locale_preference.sql",
    ROOT / "migrations" / "0246_ui_translation_ledger.sql",
    ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql",
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql",
    ROOT / "migrations" / "0247_za_ui_translation_seed_ownership_truncate_guard.sql",
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql",
    ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic.sql",
)
_SIMILAR_VOC_SEED = ROOT / "migrations" / "0249_z_similar_voc_translation_draft.sql"


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
    """Wait until a backend is blocked on a PostgreSQL lock."""
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


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_similar_voc_seed_replay_does_not_deadlock_with_owned_root_delete() -> None:
    """Seed replay and normal root retirement must share one ownership lock order."""

    async def scenario() -> None:
        database_name = f"lineageweave_similar_delete_race_{uuid.uuid4().hex[:12]}"
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
            for migration in _BASE_MIGRATIONS:
                await setup.execute(migration.read_text(encoding="utf-8"))
            await setup.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))

            resource_id = await setup.fetchval(
                """
                select resource_id
                  from public.ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            assert resource_id is not None
            assert (
                await setup.fetchval(
                    """
                    select ownership_state
                      from public.ui_translation_seed_ownership
                     where migration_key = '0249_z_similar_voc_translation_draft'
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
                 where migration_key = '0249_z_similar_voc_translation_draft'
                 for update
                """
            )

            seed_sql = _SIMILAR_VOC_SEED.read_text(encoding="utf-8")
            replay_task = asyncio.create_task(replay.execute(seed_sql))
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
                    "select count(*) from public.ui_translation_resource where resource_id = $1",
                    resource_id,
                )
                == 0
            )
            receipt = await setup.fetchrow(
                """
                select ownership_state, resource_id
                  from public.ui_translation_seed_ownership
                 where migration_key = '0249_z_similar_voc_translation_draft'
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

"""Concurrent-init regression for the Customer Master translation seed owner."""

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
_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_TRUNCATE_GUARD_MIGRATION = ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql"
_SEED_OWNERSHIP_MIGRATION = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)


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
    """Wait until the contender is blocked by the uncommitted ownership row."""
    for _ in range(100):
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
    pytest.fail("concurrent ownership initializer never reached the lock wait")


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_concurrent_seed_ownership_initializers_converge_idempotently() -> None:
    """A second first-install session must adopt the committed reservation safely."""

    async def scenario() -> None:
        database_name = f"lineageweave_customer_owner_race_{uuid.uuid4().hex[:12]}"
        admin = await asyncpg.connect(_ADMIN_DSN)
        await admin.execute(f'create database "{database_name}"')
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))

        setup: asyncpg.Connection | None = None
        blocker: asyncpg.Connection | None = None
        contender: asyncpg.Connection | None = None
        observer: asyncpg.Connection | None = None
        try:
            setup = await asyncpg.connect(database_dsn)
            for migration in (
                _INITIAL_SCHEMA,
                _MEMBER_LOCALE_MIGRATION,
                _LEDGER_MIGRATION,
                _TRUNCATE_GUARD_MIGRATION,
            ):
                await setup.execute(migration.read_text(encoding="utf-8"))

            ownership_sql = _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
            table_prefix, separator, _ = ownership_sql.partition(
                "do $customer_master_seed_ownership_init$"
            )
            assert separator
            await setup.execute(f"{table_prefix}\ncommit;")

            blocker = await asyncpg.connect(database_dsn)
            contender = await asyncpg.connect(database_dsn)
            observer = await asyncpg.connect(database_dsn)

            await blocker.execute("begin")
            await blocker.execute(
                """
                insert into ui_translation_seed_ownership(
                    migration_key,
                    product_key,
                    screen_key,
                    resource_version,
                    ownership_state
                )
                values (
                    '0248_customer_master_translation_draft',
                    'lineageweave',
                    'customer-master',
                    1,
                    'pending'
                )
                """
            )

            contender_task = asyncio.create_task(contender.execute(ownership_sql))
            await _wait_until_lock_wait(observer, contender.get_server_pid())
            await blocker.execute("commit")

            await asyncio.wait_for(contender_task, timeout=2)
            row = await setup.fetchrow(
                """
                select ownership_state, resource_id, count(*) over () as row_count
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            assert row is not None
            assert row["ownership_state"] == "pending"
            assert row["resource_id"] is None
            assert row["row_count"] == 1
        finally:
            for connection in (observer, contender, blocker, setup):
                if connection is not None and not connection.is_closed():
                    await connection.close()
            await admin.execute(f'drop database "{database_name}"')
            await admin.close()

    asyncio.run(scenario())

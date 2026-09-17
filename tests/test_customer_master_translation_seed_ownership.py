"""Ownership regression for the Customer Master translation seed migration."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Awaitable, Callable
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
_SEED_OWNERSHIP_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_CUSTOMER_MASTER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0248_customer_master_translation_draft.sql"
)
_MIGRATE_SCRIPT = ROOT / "docker" / "postgres-init" / "migrate.sh"
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")
_MIGRATION_FILE = "0248_customer_master_translation_draft.sql"


async def _postgres_available_async() -> bool:
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    return asyncio.run(_postgres_available_async())


async def _snapshot(
    connection: asyncpg.Connection, resource_id: int
) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    state = await connection.fetchval(
        "select publication_state from ui_translation_resource where resource_id = $1",
        resource_id,
    )
    rows = await connection.fetch(
        """
        select translation_key, locale, translated_text
          from ui_translation_text
         where resource_id = $1
         order by translation_key, locale
        """,
        resource_id,
    )
    return state, tuple(
        (row["translation_key"], row["locale"], row["translated_text"])
        for row in rows
    )


async def _with_database(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    database_name = f"lineageweave_customer_copy_owner_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            for migration in (
                _INITIAL_SCHEMA,
                _MEMBER_LOCALE_MIGRATION,
                _LEDGER_MIGRATION,
                _TRUNCATE_GUARD_MIGRATION,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_seed_ownership_guard_precedes_customer_master_seed() -> None:
    """Sorted replay must establish ownership before migration 0248 executes."""
    names = sorted(
        path.name
        for path in (ROOT / "migrations").glob("[0-9][0-9][0-9][0-9]_*.sql")
    )
    assert names.index(_SEED_OWNERSHIP_MIGRATION.name) < names.index(
        _CUSTOMER_MASTER_SEED.name
    )
    migrate_script = _MIGRATE_SCRIPT.read_text(encoding="utf-8")
    assert "lineageweave.migration_file=$migration_name" in migrate_script
    assert 'PGOPTIONS="$migration_pgoptions"' in migrate_script


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_seed_and_rollback_refuse_preexisting_unowned_customer_master_draft() -> None:
    """A v1 draft not created by 0248 must remain byte-for-byte operator-owned."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await connection.fetchval(
            """
            insert into ui_translation_resource(
                product_key, screen_key, resource_version
            )
            values ('lineageweave', 'customer-master', 1)
            returning resource_id
            """
        )
        await connection.execute(
            """
            insert into ui_translation_key(resource_id, translation_key)
            values ($1, 'Customer master')
            """,
            resource_id,
        )
        await connection.executemany(
            """
            insert into ui_translation_text(
                resource_id, translation_key, locale, translated_text
            )
            values ($1, 'Customer master', $2, $3)
            """,
            [
                (resource_id, locale, f"operator-owned-{locale}")
                for locale in _LOCALES
            ],
        )
        before = await _snapshot(connection, resource_id)

        await connection.execute(
            _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
        )
        assert (
            await connection.fetchval(
                """
                select ownership_state
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            == "blocked"
        )
        await connection.execute(
            "select set_config('lineageweave.migration_file', $1, false)",
            _MIGRATION_FILE,
        )

        with pytest.raises(
            asyncpg.PostgresError,
            match="refuses to adopt existing unowned Customer Master resource",
        ):
            await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
        await connection.execute("rollback")
        assert await _snapshot(connection, resource_id) == before

        with pytest.raises(
            asyncpg.PostgresError,
            match="refuses to remove unowned Customer Master resource",
        ):
            await connection.execute(
                _CUSTOMER_MASTER_ROLLBACK.read_text(encoding="utf-8")
            )
        await connection.execute("rollback")
        assert await _snapshot(connection, resource_id) == before

    asyncio.run(_with_database(scenario))


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_owned_customer_master_seed_replays_and_rolls_back_with_ownership() -> None:
    """0248 owns only the draft it creates and can replay or roll it back safely."""

    async def scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(
            _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
        )
        assert (
            await connection.fetchval(
                """
                select ownership_state
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            == "pending"
        )
        await connection.execute(
            "select set_config('lineageweave.migration_file', $1, false)",
            _MIGRATION_FILE,
        )

        await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
        resource_id = await connection.fetchval(
            """
            select resource_id
              from ui_translation_resource
             where product_key = 'lineageweave'
               and screen_key = 'customer-master'
               and resource_version = 1
            """
        )
        ownership = await connection.fetchrow(
            """
            select ownership_state, resource_id
              from ui_translation_seed_ownership
             where migration_key = '0248_customer_master_translation_draft'
            """
        )
        assert ownership["ownership_state"] == "owned"
        assert ownership["resource_id"] == resource_id

        await connection.execute(
            _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
        )
        await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'customer-master'
                   and resource_version = 1
                """
            )
            == 1
        )

        await connection.execute(
            _CUSTOMER_MASTER_ROLLBACK.read_text(encoding="utf-8")
        )
        assert (
            await connection.fetchval(
                "select count(*) from ui_translation_resource where resource_id = $1",
                resource_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            == 0
        )

        await connection.execute(
            _SEED_OWNERSHIP_ROLLBACK.read_text(encoding="utf-8")
        )
        assert await connection.fetchval(
            "select to_regclass('ui_translation_seed_ownership')"
        ) is None

    asyncio.run(_with_database(scenario))

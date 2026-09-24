"""Production-path evidence for the Customer Master translation seed."""

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
_CUSTOMER_MASTER_OWNERSHIP = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_SEED_OWNERSHIP_TRUNCATE_GUARD = (
    ROOT / "migrations" / "0247_za_ui_translation_seed_ownership_truncate_guard.sql"
)
_CUSTOMER_MASTER_REPLAY_GUARD = (
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql"
)
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_CUSTOMER_MASTER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0248_customer_master_translation_draft.sql"
)
_FORWARD_MIGRATIONS = (
    _INITIAL_SCHEMA,
    _MEMBER_LOCALE_MIGRATION,
    _LEDGER_MIGRATION,
    _TRUNCATE_GUARD_MIGRATION,
    _CUSTOMER_MASTER_OWNERSHIP,
    _SEED_OWNERSHIP_TRUNCATE_GUARD,
    _CUSTOMER_MASTER_REPLAY_GUARD,
    _CUSTOMER_MASTER_SEED,
)


async def _postgres_available_async() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    return asyncio.run(_postgres_available_async())


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


async def _apply_with_runner_provenance(
    connection: asyncpg.Connection,
    migration: Path,
    *,
    provenance: str | None = None,
) -> None:
    """Apply one SQL artifact with the same migration-file GUC used by migrate.sh."""
    migration_file = provenance or migration.name
    await connection.execute(
        "select set_config('lineageweave.migration_file', $1, false)",
        migration_file,
    )
    await connection.execute(migration.read_text(encoding="utf-8"))


async def _run_with_production_seed_db(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Apply the canonical sorted seed predecessors in an isolated database."""
    database_name = f"lineageweave_customer_seed_path_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            for migration in _FORWARD_MIGRATIONS:
                await _apply_with_runner_provenance(connection, migration)
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_customer_master_seed_production_path_is_owned_complete_and_replay_safe() -> None:
    """The guarded production path owns one complete 37×8 draft and preserves review edits."""

    async def scenario(connection: asyncpg.Connection) -> None:
        receipt = await connection.fetchrow(
            """
            select ownership_state, resource_id
              from ui_translation_seed_ownership
             where migration_key = '0248_customer_master_translation_draft'
               and product_key = 'lineageweave'
               and screen_key = 'customer-master'
               and resource_version = 1
            """
        )
        assert receipt is not None
        assert receipt["ownership_state"] == "owned"
        resource_id = receipt["resource_id"]
        assert resource_id is not None

        resource = await connection.fetchrow(
            """
            select publication_state, published_at
              from ui_translation_resource
             where resource_id = $1
            """,
            resource_id,
        )
        assert resource is not None
        assert resource["publication_state"] == "draft"
        assert resource["published_at"] is None
        assert (
            await connection.fetchval(
                "select count(*) from ui_translation_key where resource_id = $1",
                resource_id,
            )
            == 37
        )
        assert (
            await connection.fetchval(
                "select count(*) from ui_translation_text where resource_id = $1",
                resource_id,
            )
            == 37 * 8
        )
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_key as required_key
                  cross join (
                      values ('ko'), ('en'), ('ja'), ('zh'), ('vi'), ('es'), ('de'), ('fr')
                  ) as required_locale(locale)
                  left join ui_translation_text as translated
                    on translated.resource_id = required_key.resource_id
                   and translated.translation_key = required_key.translation_key
                   and translated.locale = required_locale.locale
                 where required_key.resource_id = $1
                   and translated.translation_text_id is null
                """,
                resource_id,
            )
            == 0
        )

        reviewed_key = "Customer master"
        reviewed_copy = "고객 마스터 검토본"
        await connection.execute(
            "select set_config('lineageweave.migration_file', 'test/product-review', false)"
        )
        await connection.execute(
            """
            update ui_translation_text
               set translated_text = $1
             where resource_id = $2
               and translation_key = $3
               and locale = 'ko'
            """,
            reviewed_copy,
            resource_id,
            reviewed_key,
        )

        # Direct historical replay is stricter than normal startup, which skips
        # purpose-complete owned/retired 0248. It must still preserve reviewed copy.
        await _apply_with_runner_provenance(connection, _CUSTOMER_MASTER_SEED)
        assert (
            await connection.fetchval(
                """
                select translated_text
                  from ui_translation_text
                 where resource_id = $1
                   and translation_key = $2
                   and locale = 'ko'
                """,
                resource_id,
                reviewed_key,
            )
            == reviewed_copy
        )
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
            "select set_config('lineageweave.migration_file', 'test/product-review', false)"
        )
        await connection.execute(
            """
            update ui_translation_resource
               set publication_state = 'published'
             where resource_id = $1
            """,
            resource_id,
        )
        assert (
            await connection.fetchval(
                "select publication_state from ui_translation_resource where resource_id = $1",
                resource_id,
            )
            == "published"
        )

        with pytest.raises(asyncpg.PostgresError, match="refuses to remove published"):
            await _apply_with_runner_provenance(
                connection,
                _CUSTOMER_MASTER_ROLLBACK,
                provenance="rollback/0248_customer_master_translation_draft.sql",
            )
        await connection.execute("rollback")
        assert (
            await connection.fetchval(
                "select publication_state from ui_translation_resource where resource_id = $1",
                resource_id,
            )
            == "published"
        )

    asyncio.run(_run_with_production_seed_db(scenario))


def test_customer_master_seed_production_path_rolls_back_only_exact_owned_draft() -> None:
    """The guarded rollback removes its exact draft and its ownership receipt, not operator data."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await connection.fetchval(
            """
            select resource_id
              from ui_translation_seed_ownership
             where migration_key = '0248_customer_master_translation_draft'
               and ownership_state = 'owned'
            """
        )
        assert resource_id is not None

        await _apply_with_runner_provenance(
            connection,
            _CUSTOMER_MASTER_ROLLBACK,
            provenance="rollback/0248_customer_master_translation_draft.sql",
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

    asyncio.run(_run_with_production_seed_db(scenario))

"""Recovery contract for the generic UI translation seed ownership migration."""

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
_CUSTOMER_OWNERSHIP = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_CUSTOMER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_GENERIC_OWNERSHIP = ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic.sql"
_GENERIC_OWNERSHIP_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0249_ui_translation_seed_ownership_generic.sql"
)
_SIMILAR_SEED = ROOT / "migrations" / "0249_z_similar_voc_translation_draft.sql"
_SIMILAR_SEED_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0249_z_similar_voc_translation_draft.sql"
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


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_generic_ownership_rollback_restores_customer_master_owner_lane() -> None:
    """Rollback removes only generic wiring and leaves 0248 ownership executable."""

    async def scenario() -> None:
        database_name = f"lineageweave_seed_generic_rb_{uuid.uuid4().hex[:12]}"
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
                    _CUSTOMER_OWNERSHIP,
                    _GENERIC_OWNERSHIP,
                    _SIMILAR_SEED,
                ):
                    await connection.execute(migration.read_text(encoding="utf-8"))

                await connection.execute(_SIMILAR_SEED_ROLLBACK.read_text(encoding="utf-8"))
                await connection.execute(
                    _GENERIC_OWNERSHIP_ROLLBACK.read_text(encoding="utf-8")
                )

                generic_trigger_count = await connection.fetchval(
                    """
                    select count(*)
                      from pg_trigger
                     where tgname like 'ui_translation_seed_%_ownership_%'
                       and not tgisinternal
                    """
                )
                assert generic_trigger_count == 0
                expected_customer_triggers = {
                    "customer_master_seed_resource_ownership_guard",
                    "customer_master_seed_resource_ownership_bind",
                    "customer_master_seed_key_ownership_guard",
                    "customer_master_seed_text_ownership_guard",
                }
                trigger_rows = await connection.fetch(
                    """
                    select tgname
                      from pg_trigger
                     where tgname = any($1::text[])
                       and not tgisinternal
                    """,
                    list(expected_customer_triggers),
                )
                assert {row["tgname"] for row in trigger_rows} == expected_customer_triggers

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
                assert (
                    await connection.fetchval(
                        """
                        select count(*)
                          from ui_translation_seed_ownership
                         where migration_key = '0249_z_similar_voc_translation_draft'
                        """
                    )
                    == 0
                )

                await connection.execute(
                    "select set_config('lineageweave.migration_file', $1, false)",
                    "0248_customer_master_translation_draft.sql",
                )
                await connection.execute(_CUSTOMER_SEED.read_text(encoding="utf-8"))
                assert (
                    await connection.fetchval(
                        """
                        select ownership_state
                          from ui_translation_seed_ownership
                         where migration_key = '0248_customer_master_translation_draft'
                        """
                    )
                    == "owned"
                )
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

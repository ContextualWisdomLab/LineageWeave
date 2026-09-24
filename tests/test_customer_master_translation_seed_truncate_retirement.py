"""Regression for TRUNCATE CASCADE against one-time translation seed history."""

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
_SEED_OWNERSHIP_TRUNCATE_GUARD_MIGRATION = (
    ROOT / "migrations" / "0247_za_ui_translation_seed_ownership_truncate_guard.sql"
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
    """Probe PostgreSQL once during collection without adding a sync driver."""
    return asyncio.run(_postgres_available_async())


async def _scenario() -> None:
    """Reject ledger TRUNCATE CASCADE that would erase retired seed history."""
    database_name = f"lineageweave_seed_truncate_{uuid.uuid4().hex[:12]}"
    admin = await asyncpg.connect(_ADMIN_DSN)
    await admin.execute(f'create database "{database_name}"')
    parsed = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            for migration in (
                _INITIAL_SCHEMA,
                _MEMBER_LOCALE_MIGRATION,
                _LEDGER_MIGRATION,
                _TRUNCATE_GUARD_MIGRATION,
                _SEED_OWNERSHIP_MIGRATION,
                _SEED_OWNERSHIP_TRUNCATE_GUARD_MIGRATION,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))

            await connection.execute(
                """
                update ui_translation_seed_ownership
                   set ownership_state = 'retired'
                 where migration_key = '0248_customer_master_translation_draft'
                   and ownership_state = 'pending'
                   and resource_id is null
                """
            )
            assert (
                await connection.fetchval(
                    """
                    select ownership_state
                      from ui_translation_seed_ownership
                     where migration_key = '0248_customer_master_translation_draft'
                    """
                )
                == "retired"
            )

            # ui_translation_seed_ownership references ui_translation_resource.
            # PostgreSQL therefore includes the ownership table in a root
            # TRUNCATE ... CASCADE even when the retired receipt has NULL
            # resource_id. That history must not disappear through a bulk-data
            # operation that bypasses the row-level retirement/rollback guards.
            with pytest.raises(asyncpg.PostgresError, match="seed ownership history"):
                await connection.execute("truncate table ui_translation_resource cascade")

            receipt = await connection.fetchrow(
                """
                select ownership_state, resource_id
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            assert receipt is not None
            assert receipt["ownership_state"] == "retired"
            assert receipt["resource_id"] is None
        finally:
            await connection.close()
    finally:
        await admin.execute(f'drop database "{database_name}"')
        await admin.close()


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_truncate_cascade_cannot_erase_retired_seed_history() -> None:
    """Retired one-time seed provenance survives ledger bulk-clear attempts."""
    asyncio.run(_scenario())

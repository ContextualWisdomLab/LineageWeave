"""Recovery ordering contract for the generic Similar VOC seed layer."""

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
_OWNERSHIP_TRUNCATE_GUARD_MIGRATION = (
    ROOT / "migrations" / "0247_za_ui_translation_seed_ownership_truncate_guard.sql"
)
_CUSTOMER_MASTER_REPLAY_GUARD_MIGRATION = (
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql"
)
_GENERIC_SEED_OWNERSHIP = ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic.sql"
_SIMILAR_VOC_SEED = ROOT / "migrations" / "0249_z_similar_voc_translation_draft.sql"
_SIMILAR_VOC_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0249_z_similar_voc_translation_draft.sql"
)
_PARENT_OWNERSHIP_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0247_z_customer_master_translation_seed_ownership.sql"
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


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


async def _run_in_database(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Run one rollback-order scenario in an isolated PostgreSQL database."""
    database_name = f"lineageweave_similar_voc_rollback_{uuid.uuid4().hex[:12]}"
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
                _SEED_OWNERSHIP_MIGRATION,
                _OWNERSHIP_TRUNCATE_GUARD_MIGRATION,
                _CUSTOMER_MASTER_REPLAY_GUARD_MIGRATION,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_parent_ownership_rollback_refuses_live_generic_seed_layer() -> None:
    """A base rollback cannot strand descendant generic triggers without their table."""

    async def scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_ROLLBACK.read_text(encoding="utf-8"))

        assert (
            await connection.fetchval(
                """
                select count(*)
                  from public.ui_translation_seed_ownership
                 where migration_key = '0249_z_similar_voc_translation_draft'
                """
            )
            == 0
        )

        with pytest.raises(
            asyncpg.PostgresError,
            match="generic UI translation seed layer remains",
        ):
            await connection.execute(_PARENT_OWNERSHIP_ROLLBACK.read_text(encoding="utf-8"))
        await connection.execute("rollback")

        assert (
            await connection.fetchval(
                "select to_regclass('public.ui_translation_seed_ownership') is not null"
            )
            is True
        )
        assert (
            await connection.fetchval(
                "select to_regprocedure('public.guard_ui_translation_seed_resource_ownership()') is not null"
            )
            is True
        )

    asyncio.run(_run_in_database(scenario))

"""Production-path evidence for the Customer Master translation seed."""

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
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"


async def _postgres_available_async() -> bool:
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


async def _run_current_seed_evidence_path() -> tuple[
    asyncpg.Connection, asyncpg.Connection, str
]:
    """Reproduce the current completeness fixture's migration path."""
    database_name = f"lineageweave_customer_seed_path_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    connection = await asyncpg.connect(database_dsn)
    for migration in (
        _INITIAL_SCHEMA,
        _MEMBER_LOCALE_MIGRATION,
        _LEDGER_MIGRATION,
        _TRUNCATE_GUARD_MIGRATION,
        _CUSTOMER_MASTER_SEED,
    ):
        await connection.execute(migration.read_text(encoding="utf-8"))
    return connection, admin_connection, database_name


async def _close_seed_database(
    connection: asyncpg.Connection,
    admin_connection: asyncpg.Connection,
    database_name: str,
) -> None:
    await connection.close()
    await admin_connection.execute(f'drop database "{database_name}"')
    await admin_connection.close()


def test_customer_master_seed_evidence_uses_production_ownership_path() -> None:
    """The completeness evidence must traverse the production ownership boundary."""

    async def scenario() -> None:
        connection, admin_connection, database_name = (
            await _run_current_seed_evidence_path()
        )
        try:
            receipt = await connection.fetchrow(
                """
                select ownership_state, resource_id
                  from ui_translation_seed_ownership
                 where migration_key = '0248_customer_master_translation_draft'
                """
            )
            assert receipt is not None
            assert receipt["ownership_state"] == "owned"
            assert receipt["resource_id"] is not None
        finally:
            await _close_seed_database(connection, admin_connection, database_name)

    asyncio.run(scenario())

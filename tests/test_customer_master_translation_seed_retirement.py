"""Lifecycle regression for the one-time Customer Master translation seed receipt."""

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
_SEED_REPLAY_GUARD_MIGRATION = (
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql"
)
_SEED_OWNERSHIP_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_MIGRATE_SCRIPT = ROOT / "docker" / "postgres-init" / "migrate.sh"
_MIGRATION_FILE = "0248_customer_master_translation_draft.sql"


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
    """Delete a reviewed seed candidate without reviving historical seed authority."""
    database_name = f"lineageweave_customer_seed_retire_{uuid.uuid4().hex[:12]}"
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
                _SEED_REPLAY_GUARD_MIGRATION,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))

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
            assert isinstance(resource_id, int)
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

            # Once created, the candidate becomes operator/reviewer-owned data.
            # Deleting it intentionally must retire the one-time seed receipt;
            # startup must never resurrect historical copy just because the FK
            # target disappeared.
            await connection.execute(
                "select set_config('lineageweave.migration_file', '', false)"
            )
            await connection.execute(
                "delete from ui_translation_resource where resource_id = $1",
                resource_id,
            )
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

            # Replaying the ownership migration must preserve retirement instead
            # of reopening a pending seed reservation.
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
                == "retired"
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
                == 0
            )

            # The retirement receipt is the durable no-resurrection fact. An
            # ownership-boundary rollback must fail closed rather than erase it
            # and re-authorize historical 0248 bytes on a later reapply.
            with pytest.raises(asyncpg.PostgresError, match="retired"):
                await connection.execute(
                    _SEED_OWNERSHIP_ROLLBACK.read_text(encoding="utf-8")
                )
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


def test_migration_runner_treats_retired_seed_as_purpose_complete() -> None:
    """Normal startup skips historical 0248 after a reviewed candidate is retired."""
    script = _MIGRATE_SCRIPT.read_text(encoding="utf-8")
    assert "owned|retired)" in script
    seed_gate = script.index('if [ "$migration_name" = "0248_customer_master_translation_draft.sql" ]')
    retirement_gate = script.index("owned|retired)", seed_gate)
    skip = script.index("continue", retirement_gate)
    generic_apply = script.index("printf 'Applying %s", skip)
    assert seed_gate < retirement_gate < skip < generic_apply


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_deleting_owned_candidate_retires_seed_without_reopening_historical_copy() -> None:
    """An ordinary delete preserves the one-time seed completion receipt."""
    asyncio.run(_scenario())

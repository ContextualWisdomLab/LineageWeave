"""Upgrade regression for Customer Master one-time seed retirement constraints."""

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

_OLD_NAMED_OWNERSHIP_TABLE = """
create table ui_translation_seed_ownership (
    migration_key text primary key,
    product_key text not null,
    screen_key text not null,
    resource_version bigint not null check (resource_version > 0),
    resource_id bigint unique
        references ui_translation_resource(resource_id) on delete cascade,
    ownership_state text not null,
    constraint ui_translation_seed_ownership_state_ck
        check (ownership_state in ('pending', 'owned', 'blocked')),
    unique (product_key, screen_key, resource_version),
    constraint ui_translation_seed_ownership_shape_ck
        check (
            (ownership_state = 'owned' and resource_id is not null)
            or (
                ownership_state in ('pending', 'blocked')
                and resource_id is null
            )
        )
);
"""


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
    """Upgrade old named checks before an owned candidate can retire."""
    database_name = f"lineageweave_customer_seed_upgrade_{uuid.uuid4().hex[:12]}"
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
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))

            resource_id = await connection.fetchval(
                """
                insert into ui_translation_resource(
                    product_key,
                    screen_key,
                    resource_version
                )
                values ('lineageweave', 'customer-master', 1)
                returning resource_id
                """
            )
            assert isinstance(resource_id, int)

            # Model an installation created by the predecessor migration. The
            # named constraints already exist, but their definitions predate the
            # retired one-time-seed receipt.
            await connection.execute(_OLD_NAMED_OWNERSHIP_TABLE)
            await connection.execute(
                """
                insert into ui_translation_seed_ownership(
                    migration_key,
                    product_key,
                    screen_key,
                    resource_version,
                    resource_id,
                    ownership_state
                )
                values (
                    '0248_customer_master_translation_draft',
                    'lineageweave',
                    'customer-master',
                    1,
                    $1,
                    'owned'
                )
                """,
                resource_id,
            )

            await connection.execute(
                _SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8")
            )

            definitions = {
                row["conname"]: row["definition"]
                for row in await connection.fetch(
                    """
                    select conname, pg_get_constraintdef(oid) as definition
                      from pg_constraint
                     where conrelid = 'public.ui_translation_seed_ownership'::regclass
                       and conname in (
                           'ui_translation_seed_ownership_state_ck',
                           'ui_translation_seed_ownership_shape_ck'
                       )
                    """
                )
            }
            assert "retired" in definitions["ui_translation_seed_ownership_state_ck"]
            assert "retired" in definitions["ui_translation_seed_ownership_shape_ck"]

            # The upgraded constraints must make the new retirement path usable
            # on an installation that already had the old, identically named
            # checks. Replaying the migration again must remain idempotent.
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
def test_existing_named_ownership_checks_upgrade_to_retirement_contract() -> None:
    """Existing predecessor constraints are replaced before retirement is used."""
    asyncio.run(_scenario())

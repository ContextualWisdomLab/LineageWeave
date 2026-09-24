"""Rollback provenance must not move translation children out of a governed resource."""

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
_EXISTING_SEED_OWNERSHIP = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_GENERIC_SEED_OWNERSHIP = (
    ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic.sql"
)
_GENERIC_CHILD_UPDATE_GUARD = (
    ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic_b.sql"
)
_SIMILAR_VOC_SEED = ROOT / "migrations" / "0249_z_similar_voc_translation_draft.sql"
_ROLLBACK_FILE = "rollback/0249_z_similar_voc_translation_draft.sql"


def test_child_update_guard_replays_after_generic_owner_before_similar_voc_seed() -> None:
    """Sorted migration replay must install the hardened guard before seed writes."""
    names = sorted(path.name for path in (ROOT / "migrations").glob("*.sql"))
    assert names.index(_GENERIC_SEED_OWNERSHIP.name) < names.index(
        _GENERIC_CHILD_UPDATE_GUARD.name
    ) < names.index(_SIMILAR_VOC_SEED.name)


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
def test_rollback_context_cannot_move_blocked_child_to_unowned_resource() -> None:
    """UPDATE must not escape rollback provenance by changing resource_id first."""

    async def scenario() -> None:
        database_name = f"lineageweave_seed_child_move_{uuid.uuid4().hex[:12]}"
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
                    _EXISTING_SEED_OWNERSHIP,
                ):
                    await connection.execute(migration.read_text(encoding="utf-8"))

                blocked_resource_id = await connection.fetchval(
                    """
                    insert into ui_translation_resource(
                        product_key, screen_key, resource_version
                    )
                    values ('lineageweave', 'similar-voc', 1)
                    returning resource_id
                    """
                )
                target_resource_id = await connection.fetchval(
                    """
                    insert into ui_translation_resource(
                        product_key, screen_key, resource_version
                    )
                    values ('lineageweave', 'unowned-target', 1)
                    returning resource_id
                    """
                )
                await connection.execute(
                    """
                    insert into ui_translation_key(resource_id, translation_key)
                    values ($1, 'operator-owned-copy')
                    """,
                    blocked_resource_id,
                )

                await connection.execute(
                    _GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8")
                )
                await connection.execute(
                    _GENERIC_CHILD_UPDATE_GUARD.read_text(encoding="utf-8")
                )
                assert (
                    await connection.fetchval(
                        """
                        select ownership_state
                          from ui_translation_seed_ownership
                         where migration_key = '0249_z_similar_voc_translation_draft'
                        """
                    )
                    == "blocked"
                )

                await connection.execute(
                    "select set_config('lineageweave.migration_file', $1, false)",
                    _ROLLBACK_FILE,
                )
                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refuses child mutation outside exact seed ownership",
                ):
                    await connection.execute(
                        """
                        update ui_translation_key
                           set resource_id = $1
                         where resource_id = $2
                           and translation_key = 'operator-owned-copy'
                        """,
                        target_resource_id,
                        blocked_resource_id,
                    )

                assert (
                    await connection.fetchval(
                        """
                        select resource_id
                          from ui_translation_key
                         where translation_key = 'operator-owned-copy'
                        """
                    )
                    == blocked_resource_id
                )
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

"""Translation child resource identity remains owned by the base ledger boundary."""

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
_DUPLICATE_CHILD_MOVE_GUARD = (
    ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic_b.sql"
)
_ROLLBACK_FILE = "rollback/0249_z_similar_voc_translation_draft.sql"


def test_seed_owner_does_not_duplicate_base_child_move_boundary() -> None:
    """ADR 0362, not a seed-specific migration, owns cross-resource child moves."""
    assert not _DUPLICATE_CHILD_MOVE_GUARD.exists()


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
def test_base_ledger_guard_blocks_key_and_text_resource_moves_under_seed_context() -> None:
    """Rollback provenance cannot bypass the ledger's immutable child resource identity."""

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
                translation_text_id = await connection.fetchval(
                    """
                    insert into ui_translation_text(
                        resource_id, translation_key, locale, translated_text
                    )
                    values ($1, 'operator-owned-copy', 'en', 'Operator-owned copy')
                    returning translation_text_id
                    """,
                    blocked_resource_id,
                )

                await connection.execute(
                    _GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8")
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
                    match="UI translation child rows cannot move between resources",
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

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="UI translation child rows cannot move between resources",
                ):
                    await connection.execute(
                        """
                        update ui_translation_text
                           set resource_id = $1
                         where translation_text_id = $2
                        """,
                        target_resource_id,
                        translation_text_id,
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
                assert (
                    await connection.fetchval(
                        """
                        select resource_id
                          from ui_translation_text
                         where translation_text_id = $1
                        """,
                        translation_text_id,
                    )
                    == blocked_resource_id
                )
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

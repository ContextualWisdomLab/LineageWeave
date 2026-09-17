"""Replay safety for reviewed Customer Master translation drafts."""

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
_REVIEW_PRESERVATION_MIGRATION = (
    ROOT / "migrations" / "0247_zz_customer_master_translation_seed_replay_guard.sql"
)
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_MIGRATE_SCRIPT = ROOT / "docker" / "postgres-init" / "migrate.sh"
_MIGRATION_FILE = "0248_customer_master_translation_draft.sql"
_REVIEWED_COPY = "검토 완료된 고객 마스터"


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


def test_review_preservation_guard_precedes_customer_master_seed() -> None:
    """Sorted startup replay must install preservation before the one-time seed."""
    names = sorted(
        path.name
        for path in (ROOT / "migrations").glob("[0-9][0-9][0-9][0-9]_*.sql")
    )
    assert names.index(_SEED_OWNERSHIP_MIGRATION.name) < names.index(
        _REVIEW_PRESERVATION_MIGRATION.name
    ) < names.index(_CUSTOMER_MASTER_SEED.name)

    migrate_script = _MIGRATE_SCRIPT.read_text(encoding="utf-8")
    skip_guard = migrate_script.index(
        'if [ "$migration_name" = "0248_customer_master_translation_draft.sql" ]'
    )
    owned_guard = migrate_script.index(
        'if [ "$customer_master_seed_state" = "owned" ]', skip_guard
    )
    skip_step = migrate_script.index("continue", owned_guard)
    apply_step = migrate_script.index("printf 'Applying %s", skip_step)
    assert skip_guard < owned_guard < skip_step < apply_step
    assert "public.ui_translation_seed_ownership" in migrate_script[skip_guard:apply_step]


async def _with_seed_database(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Run a reviewed-copy replay scenario in an isolated migrated database."""
    database_name = f"lineageweave_customer_review_{uuid.uuid4().hex[:12]}"
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
                _REVIEW_PRESERVATION_MIGRATION,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))
            await connection.execute(
                "select set_config('lineageweave.migration_file', $1, false)",
                _MIGRATION_FILE,
            )
            await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
            await connection.execute(
                "select set_config('lineageweave.migration_file', '', false)"
            )
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


async def _review_korean_customer_master_copy(connection: asyncpg.Connection) -> int:
    """Apply a legitimate draft review edit outside migration provenance."""
    resource_id = await connection.fetchval(
        """
        select resource_id
          from ui_translation_resource
         where product_key = 'lineageweave'
           and screen_key = 'customer-master'
           and resource_version = 1
        """
    )
    await connection.execute(
        """
        update ui_translation_text
           set translated_text = $1
         where resource_id = $2
           and translation_key = 'Customer master'
           and locale = 'ko'
        """,
        _REVIEWED_COPY,
        resource_id,
    )
    return resource_id


async def _direct_seed_replay(connection: asyncpg.Connection) -> None:
    """Replay 0248 directly to exercise the migration-level draft guard."""
    await connection.execute(_SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8"))
    await connection.execute(_REVIEW_PRESERVATION_MIGRATION.read_text(encoding="utf-8"))
    await connection.execute(
        "select set_config('lineageweave.migration_file', $1, false)",
        _MIGRATION_FILE,
    )
    await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
    await connection.execute("select set_config('lineageweave.migration_file', '', false)")


async def _startup_seed_step(connection: asyncpg.Connection) -> None:
    """Model migrate.sh admission for the purpose-complete Customer Master seed."""
    await connection.execute(_SEED_OWNERSHIP_MIGRATION.read_text(encoding="utf-8"))
    await connection.execute(_REVIEW_PRESERVATION_MIGRATION.read_text(encoding="utf-8"))
    ownership_state = await connection.fetchval(
        """
        select ownership_state
          from public.ui_translation_seed_ownership
         where migration_key = '0248_customer_master_translation_draft'
           and product_key = 'lineageweave'
           and screen_key = 'customer-master'
           and resource_version = 1
        """
    )
    if ownership_state == "owned":
        return
    await connection.execute(
        "select set_config('lineageweave.migration_file', $1, false)",
        _MIGRATION_FILE,
    )
    await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
    await connection.execute("select set_config('lineageweave.migration_file', '', false)")


def test_direct_seed_replay_preserves_reviewed_draft_copy() -> None:
    """Direct draft replay must not overwrite language-review edits."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await _review_korean_customer_master_copy(connection)
        await _direct_seed_replay(connection)
        assert (
            await connection.fetchval(
                """
                select translated_text
                  from ui_translation_text
                 where resource_id = $1
                   and translation_key = 'Customer master'
                   and locale = 'ko'
                """,
                resource_id,
            )
            == _REVIEWED_COPY
        )

    asyncio.run(_with_seed_database(scenario))


def test_startup_replay_skips_reviewed_published_copy() -> None:
    """Purpose-complete seed admission must preserve immutable reviewed publication."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await _review_korean_customer_master_copy(connection)
        await connection.execute(
            """
            update ui_translation_resource
               set publication_state = 'published'
             where resource_id = $1
            """,
            resource_id,
        )
        await _startup_seed_step(connection)
        row = await connection.fetchrow(
            """
            select r.publication_state, t.translated_text
              from ui_translation_resource as r
              join ui_translation_text as t on t.resource_id = r.resource_id
             where r.resource_id = $1
               and t.translation_key = 'Customer master'
               and t.locale = 'ko'
            """,
            resource_id,
        )
        assert row["publication_state"] == "published"
        assert row["translated_text"] == _REVIEWED_COPY

    asyncio.run(_with_seed_database(scenario))

"""Ownership regression for the Customer Master translation seed migration."""

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
_CUSTOMER_MASTER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0248_customer_master_translation_draft.sql"
)
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")


async def _postgres_available_async() -> bool:
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    return asyncio.run(_postgres_available_async())


async def _snapshot(
    connection: asyncpg.Connection, resource_id: int
) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    state = await connection.fetchval(
        "select publication_state from ui_translation_resource where resource_id = $1",
        resource_id,
    )
    rows = await connection.fetch(
        """
        select translation_key, locale, translated_text
          from ui_translation_text
         where resource_id = $1
         order by translation_key, locale
        """,
        resource_id,
    )
    return state, tuple(
        (row["translation_key"], row["locale"], row["translated_text"])
        for row in rows
    )


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_seed_and_rollback_refuse_preexisting_unowned_customer_master_draft() -> None:
    """A v1 draft not created by 0248 must remain byte-for-byte operator-owned."""

    async def scenario() -> None:
        database_name = f"lineageweave_customer_copy_owner_{uuid.uuid4().hex[:12]}"
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
                ):
                    await connection.execute(migration.read_text(encoding="utf-8"))

                resource_id = await connection.fetchval(
                    """
                    insert into ui_translation_resource(
                        product_key, screen_key, resource_version
                    )
                    values ('lineageweave', 'customer-master', 1)
                    returning resource_id
                    """
                )
                await connection.execute(
                    """
                    insert into ui_translation_key(resource_id, translation_key)
                    values ($1, 'Customer master')
                    """,
                    resource_id,
                )
                await connection.executemany(
                    """
                    insert into ui_translation_text(
                        resource_id, translation_key, locale, translated_text
                    )
                    values ($1, 'Customer master', $2, $3)
                    """,
                    [
                        (resource_id, locale, f"operator-owned-{locale}")
                        for locale in _LOCALES
                    ],
                )
                before = await _snapshot(connection, resource_id)

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refuses to adopt existing unowned Customer Master resource",
                ):
                    await connection.execute(
                        _CUSTOMER_MASTER_SEED.read_text(encoding="utf-8")
                    )
                await connection.execute("rollback")
                assert await _snapshot(connection, resource_id) == before

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refuses to remove unowned Customer Master resource",
                ):
                    await connection.execute(
                        _CUSTOMER_MASTER_ROLLBACK.read_text(encoding="utf-8")
                    )
                await connection.execute("rollback")
                assert await _snapshot(connection, resource_id) == before
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

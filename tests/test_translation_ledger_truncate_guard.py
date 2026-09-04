"""Regression contract for published translation-ledger TRUNCATE protection."""

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
_TRANSLATION_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")


async def _postgres_available_async() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    """Probe PostgreSQL without introducing a synchronous database driver."""
    return asyncio.run(_postgres_available_async())


async def _run_published_resource_scenario() -> None:
    """Publish one complete resource and require TRUNCATE to preserve it."""
    database_name = f"lineageweave_translation_truncate_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            await connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
            await connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
            await connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            resource_id = await connection.fetchval(
                """
                insert into ui_translation_resource(product_key, screen_key, resource_version)
                values ('lineageweave', 'customer-master', 1)
                returning resource_id
                """
            )
            assert isinstance(resource_id, int)
            await connection.execute(
                "insert into ui_translation_key(resource_id, translation_key) values ($1, 'title')",
                resource_id,
            )
            for locale in _LOCALES:
                await connection.execute(
                    """
                    insert into ui_translation_text(
                        resource_id, translation_key, locale, translated_text
                    )
                    values ($1, 'title', $2, $3)
                    """,
                    resource_id,
                    locale,
                    f"title-{locale}",
                )
            await connection.execute(
                """
                update ui_translation_resource
                   set publication_state = 'published'
                 where resource_id = $1
                """,
                resource_id,
            )

            with pytest.raises(asyncpg.PostgresError) as raised:
                await connection.execute("truncate table ui_translation_text")
            assert raised.value.sqlstate == "P0001"
            assert "immutable" in str(raised.value)
            assert await connection.fetchval(
                "select count(*) from ui_translation_text where resource_id = $1",
                resource_id,
            ) == len(_LOCALES)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_migration_installs_statement_level_truncate_guards() -> None:
    """Hosted verification must bind every ledger relation to a TRUNCATE guard."""
    sql = _TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8").lower()
    assert "create or replace function guard_ui_translation_truncate()" in sql
    assert "publication_state = 'published'" in sql
    for table in ("ui_translation_resource", "ui_translation_key", "ui_translation_text"):
        assert f"before truncate on {table}" in sql


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_postgres_rejects_truncate_after_publication() -> None:
    """TRUNCATE cannot bypass immutable published child-row protection."""
    asyncio.run(_run_published_resource_scenario())

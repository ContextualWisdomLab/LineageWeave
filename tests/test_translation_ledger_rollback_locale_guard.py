"""Recovery admission for post-0246 member locale preferences."""

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
_TRANSLATION_LEDGER_ROLLBACK = ROOT / "migrations" / "rollback" / "0246_ui_translation_ledger.sql"


def test_translation_ledger_rollback_guards_post0246_member_locales_before_ddl() -> None:
    """Rollback must name and reject member data that the old locale constraint cannot represent."""
    sql = _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8").lower()
    guard_index = sql.index("refusing 0246 rollback because post-0246 member locale preferences exist")
    ddl_index = sql.index("alter table user_account")

    assert "from user_account" in sql[:ddl_index]
    assert "preferred_locale not in ('en', 'ko', 'zh', 'ja', 'vi')" in sql[:ddl_index]
    assert guard_index < ddl_index


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
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_refuses_post0246_member_locale_without_mutation() -> None:
    """An es/de/fr member preference must survive a refused schema rollback unchanged."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_locale_guard_{uuid.uuid4().hex[:12]}"
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
                account_id = await connection.fetchval(
                    """
                    insert into user_account(external_subject_id, display_name, email_address, preferred_locale)
                    values ('rollback-locale-guard', 'Rollback Locale Guard', 'rollback-locale@example.invalid', 'es')
                    returning user_account_id
                    """
                )

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refusing 0246 rollback because post-0246 member locale preferences exist",
                ):
                    await connection.execute(_TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8"))
                await connection.execute("rollback")

                assert await connection.fetchval(
                    "select preferred_locale from user_account where user_account_id = $1",
                    account_id,
                ) == "es"
                assert await connection.fetchval(
                    "select to_regclass('ui_translation_resource')::text"
                ) == "ui_translation_resource"
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

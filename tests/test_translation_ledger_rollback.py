"""Rollback contract for the versioned UI translation-ledger migration."""

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
_TRANSLATION_LEDGER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0246_ui_translation_ledger.sql"
)


def test_translation_ledger_migration_has_executable_rollback_contract() -> None:
    """A deployable schema foundation must carry its dependency-safe recovery path."""
    assert _TRANSLATION_LEDGER_ROLLBACK.is_file()
    sql = _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8").lower()

    for fragment in (
        "drop table if exists ui_translation_text",
        "drop table if exists ui_translation_key",
        "drop table if exists ui_translation_resource",
        "drop function if exists guard_ui_translation_child_mutation()",
        "drop function if exists guard_ui_translation_resource_mutation()",
        "add constraint user_account_preferred_locale_ck",
        "'en', 'ko', 'zh', 'ja', 'vi'",
        "from ui_translation_resource",
        "refusing 0246 rollback because translation resources exist",
    ):
        assert fragment in sql

    for unsupported_pre0246_locale in ("'es'", "'de'", "'fr'"):
        assert unsupported_pre0246_locale not in sql


async def _postgres_available_async() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    """Probe PostgreSQL once during collection without adding a sync DB driver."""
    return asyncio.run(_postgres_available_async())


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_restores_pre0246_schema_projection() -> None:
    """Apply 0246 then rollback and recover the five-locale member projection."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_{uuid.uuid4().hex[:12]}"
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
                await connection.execute(_TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8"))

                for relation in (
                    "ui_translation_text",
                    "ui_translation_key",
                    "ui_translation_resource",
                ):
                    assert await connection.fetchval("select to_regclass($1)", relation) is None

                constraint_definition = await connection.fetchval(
                    """
                    select pg_get_constraintdef(oid)
                      from pg_constraint
                     where conname = 'user_account_preferred_locale_ck'
                    """
                )
                assert constraint_definition is not None
                for locale in ("en", "ko", "zh", "ja", "vi"):
                    assert f"'{locale}'" in constraint_definition
                for locale in ("es", "de", "fr"):
                    assert f"'{locale}'" not in constraint_definition
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_translation_ledger_rollback_refuses_existing_translation_data() -> None:
    """Recovery must not erase draft or published customer copy contrary to ADR 0362."""

    async def scenario() -> None:
        database_name = f"lineageweave_translation_rollback_guard_{uuid.uuid4().hex[:12]}"
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
                await connection.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values ('lineageweave', 'customer-master', 1)
                    """
                )

                with pytest.raises(
                    asyncpg.PostgresError,
                    match="refusing 0246 rollback because translation resources exist",
                ):
                    await connection.execute(
                        _TRANSLATION_LEDGER_ROLLBACK.read_text(encoding="utf-8")
                    )
                await connection.execute("rollback")

                assert (
                    await connection.fetchval(
                        "select to_regclass('ui_translation_resource')::text"
                    )
                    == "ui_translation_resource"
                )
                assert await connection.fetchval(
                    "select count(*) from ui_translation_resource"
                ) == 1
            finally:
                await connection.close()
        finally:
            await admin_connection.execute(f'drop database "{database_name}"')
            await admin_connection.close()

    asyncio.run(scenario())

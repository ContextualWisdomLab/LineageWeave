"""Collation-independent whitespace contracts for versioned UI translations."""

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
_TRANSLATION_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")
_EXPECTED_WHITESPACE_CODEPOINTS = {
    9,
    10,
    11,
    12,
    13,
    28,
    29,
    30,
    31,
    32,
    133,
    160,
    5760,
    8192,
    8193,
    8194,
    8195,
    8196,
    8197,
    8198,
    8199,
    8200,
    8201,
    8202,
    8232,
    8233,
    8239,
    8287,
    12288,
}


async def _postgres_available_async() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = await asyncpg.connect(_ADMIN_DSN, timeout=2)
    except (asyncpg.PostgresError, OSError, TimeoutError):
        return False
    await connection.close()
    return True


def _postgres_available() -> bool:
    """Probe PostgreSQL once without adding a synchronous database driver."""
    return asyncio.run(_postgres_available_async())


async def _run_with_c_locale_translation_db(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Apply the ledger migrations in a deterministic C-locale throwaway database."""
    database_name = f"lineageweave_translation_c_test_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(
        f'create database "{database_name}" template template0 encoding \'UTF8\' lc_collate \'C\' lc_ctype \'C\''
    )
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            await connection.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
            await connection.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
            await connection.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


async def _assert_check_violation(operation: Awaitable[object]) -> None:
    """Require the database schema to reject one invalid value at admission."""
    try:
        await operation
    except asyncpg.PostgresError as exc:
        assert exc.sqlstate == "23514"
        return
    raise AssertionError("expected PostgreSQL check-constraint rejection")


def test_whitespace_contract_is_explicit_and_not_posix_locale_dependent() -> None:
    """Database and Python admission share one explicit Unicode whitespace repertoire."""
    migration = _TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8")
    source = (ROOT / "backend" / "app" / "translation_ledger.py").read_text(encoding="utf-8")

    assert "_UI_WHITESPACE_CODEPOINTS" in source
    assert "strip(_UI_WHITESPACE)" in source
    for codepoint in _EXPECTED_WHITESPACE_CODEPOINTS:
        assert f"chr({codepoint})" in migration
    assert "!~ E'^\\\\s|\\\\s$'" not in migration
    assert "!~ E'^\\\\s*$'" not in migration


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_c_locale_rejects_unicode_edge_whitespace_and_blank_copy() -> None:
    """A valid C-locale deployment cannot publish values Python treats as whitespace."""

    async def scenario(connection: asyncpg.Connection) -> None:
        for product_key, screen_key in (
            ("\u00a0lineageweave", "customer-master"),
            ("lineageweave", "customer-master\u3000"),
        ):
            await _assert_check_violation(
                connection.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values ($1, $2, 1)
                    """,
                    product_key,
                    screen_key,
                )
            )

        resource_id = await connection.fetchval(
            """
            insert into ui_translation_resource(product_key, screen_key, resource_version)
            values ('lineageweave', 'customer-master', 2)
            returning resource_id
            """
        )
        assert isinstance(resource_id, int)
        await connection.execute(
            """
            insert into ui_translation_key(resource_id, translation_key)
            values ($1, 'title')
            """,
            resource_id,
        )
        for locale in _LOCALES:
            await connection.execute(
                """
                insert into ui_translation_text(resource_id, translation_key, locale, translated_text)
                values ($1, 'title', $2, $3)
                """,
                resource_id,
                locale,
                f"title-{locale}",
            )

        for blank_copy in ("\u00a0", "\u3000", "\u00a0\u3000"):
            await _assert_check_violation(
                connection.execute(
                    """
                    update ui_translation_text
                       set translated_text = $1
                     where resource_id = $2
                       and translation_key = 'title'
                       and locale = 'en'
                    """,
                    blank_copy,
                    resource_id,
                )
            )

    asyncio.run(_run_with_c_locale_translation_db(scenario))

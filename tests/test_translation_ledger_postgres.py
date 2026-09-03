"""Real-PostgreSQL verification for the versioned UI translation ledger."""

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


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


async def _run_with_translation_db(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Apply real migrations in a throwaway database and run one scenario."""
    database_name = f"lineageweave_translation_test_{uuid.uuid4().hex[:12]}"
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
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


async def _seed_complete_draft(
    connection: asyncpg.Connection,
    *,
    version: int = 1,
) -> int:
    """Create one synthetic complete eight-locale draft and return its resource id."""
    resource_id = await connection.fetchval(
        """
        insert into ui_translation_resource(product_key, screen_key, resource_version)
        values ('lineageweave', 'customer-master', $1)
        returning resource_id
        """,
        version,
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
            insert into ui_translation_text(
                resource_id,
                translation_key,
                locale,
                translated_text
            )
            values ($1, 'title', $2, $3)
            """,
            resource_id,
            locale,
            f"title-{locale}",
        )
    return resource_id


async def _assert_postgres_error(
    operation: Awaitable[object],
    *,
    sqlstate: str,
    message_fragment: str | None = None,
) -> None:
    """Require one exact PostgreSQL SQLSTATE and optional server-message fragment."""
    try:
        await operation
    except asyncpg.PostgresError as exc:
        assert exc.sqlstate == sqlstate
        if message_fragment is not None:
            assert message_fragment in str(exc)
        return
    raise AssertionError(f"expected PostgreSQL SQLSTATE {sqlstate}")


def test_postgres_rejects_padded_translation_resource_identity() -> None:
    """Database aggregate identity cannot diverge from reader/cache admission."""

    async def scenario(connection: asyncpg.Connection) -> None:
        for product_key, screen_key in (
            ("lineageweave ", "customer-master"),
            ("lineageweave", " customer-master"),
            ("lineageweave\t", "customer-master"),
            ("lineageweave", "\ncustomer-master"),
        ):
            await _assert_postgres_error(
                connection.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values ($1, $2, 1)
                    """,
                    product_key,
                    screen_key,
                ),
                sqlstate="23514",
            )

    asyncio.run(_run_with_translation_db(scenario))


def test_postgres_rejects_padded_required_translation_key_identity() -> None:
    """Required screen-copy identifiers cannot differ only by edge whitespace."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await connection.fetchval(
            """
            insert into ui_translation_resource(product_key, screen_key, resource_version)
            values ('lineageweave', 'customer-master', 1)
            returning resource_id
            """
        )
        assert isinstance(resource_id, int)
        for translation_key in (" title", "title ", "\ttitle", "title\n"):
            await _assert_postgres_error(
                connection.execute(
                    """
                    insert into ui_translation_key(resource_id, translation_key)
                    values ($1, $2)
                    """,
                    resource_id,
                    translation_key,
                ),
                sqlstate="23514",
            )

    asyncio.run(_run_with_translation_db(scenario))


def test_postgres_translation_resource_identity_is_immutable_after_creation() -> None:
    """A reviewed draft cannot be retargeted to another product, screen, or version."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await _seed_complete_draft(connection, version=3)
        for column, value in (
            ("product_key", "other-product"),
            ("screen_key", "other-screen"),
            ("resource_version", "4"),
        ):
            await _assert_postgres_error(
                connection.execute(
                    f"update ui_translation_resource set {column} = $1 where resource_id = $2",
                    value if column != "resource_version" else int(value),
                    resource_id,
                ),
                sqlstate="P0001",
                message_fragment="identity is immutable",
            )

        identity = await connection.fetchrow(
            """
            select product_key, screen_key, resource_version
              from ui_translation_resource
             where resource_id = $1
            """,
            resource_id,
        )
        assert identity is not None
        assert tuple(identity.values()) == ("lineageweave", "customer-master", 3)

    asyncio.run(_run_with_translation_db(scenario))


def test_postgres_publication_timestamp_is_database_owned_and_transition_scoped() -> None:
    """Caller input and transaction age cannot forge the immutable publication receipt."""

    async def scenario(connection: asyncpg.Connection) -> None:
        transaction = connection.transaction()
        await transaction.start()
        try:
            resource_id = await _seed_complete_draft(connection)
            await connection.execute("select pg_sleep(0.01)")
            receipt_is_later = await connection.fetchval(
                """
                update ui_translation_resource
                   set publication_state = 'published',
                       published_at = timestamptz '2000-01-01 00:00:00+00'
                 where resource_id = $1
             returning published_at > transaction_timestamp()
                """,
                resource_id,
            )
            assert receipt_is_later is True
        except BaseException:
            await transaction.rollback()
            raise
        else:
            await transaction.commit()

        await _assert_postgres_error(
            connection.execute(
                """
                update ui_translation_resource
                   set published_at = statement_timestamp()
                 where resource_id = $1
                """,
                resource_id,
            ),
            sqlstate="P0001",
            message_fragment="immutable",
        )

    asyncio.run(_run_with_translation_db(scenario))


def test_postgres_publication_fails_closed_when_one_locale_is_missing() -> None:
    """The database itself rejects an incomplete required-key × locale matrix."""

    async def scenario(connection: asyncpg.Connection) -> None:
        transaction = connection.transaction()
        await transaction.start()
        try:
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
            for locale in _LOCALES[:-1]:
                await connection.execute(
                    """
                    insert into ui_translation_text(
                        resource_id,
                        translation_key,
                        locale,
                        translated_text
                    )
                    values ($1, 'title', $2, $3)
                    """,
                    resource_id,
                    locale,
                    f"title-{locale}",
                )

            await _assert_postgres_error(
                connection.execute(
                    """
                    update ui_translation_resource
                       set publication_state = 'published'
                     where resource_id = $1
                    """,
                    resource_id,
                ),
                sqlstate="P0001",
                message_fragment="incomplete",
            )
        finally:
            await transaction.rollback()

    asyncio.run(_run_with_translation_db(scenario))

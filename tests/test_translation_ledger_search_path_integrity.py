"""PostgreSQL regressions for temporary-relation shadowing of ledger guards."""

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


async def _with_database(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
    *,
    include_truncate_guard: bool = False,
) -> None:
    database_name = f"lineageweave_translation_path_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            migrations = [
                _INITIAL_SCHEMA,
                _MEMBER_LOCALE_MIGRATION,
                _LEDGER_MIGRATION,
            ]
            if include_truncate_guard:
                migrations.append(_TRUNCATE_GUARD_MIGRATION)
            for migration in migrations:
                await connection.execute(migration.read_text(encoding="utf-8"))
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


async def _create_complete_resource(connection: asyncpg.Connection) -> int:
    resource_id = await connection.fetchval(
        """
        insert into public.ui_translation_resource(
            product_key, screen_key, resource_version
        )
        values ('lineageweave', 'search-path-regression', 1)
        returning resource_id
        """
    )
    await connection.execute(
        """
        insert into public.ui_translation_key(resource_id, translation_key)
        values ($1, 'label')
        """,
        resource_id,
    )
    await connection.executemany(
        """
        insert into public.ui_translation_text(
            resource_id, translation_key, locale, translated_text
        )
        values ($1, 'label', $2, $3)
        """,
        [(resource_id, locale, f"label-{locale}") for locale in _LOCALES],
    )
    await connection.execute(
        """
        update public.ui_translation_resource
           set publication_state = 'published'
         where resource_id = $1
        """,
        resource_id,
    )
    return resource_id


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_publication_guard_ignores_pg_temp_child_shadow() -> None:
    """TEMP child tables must not make incomplete permanent copy publishable."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await connection.fetchval(
            """
            insert into public.ui_translation_resource(
                product_key, screen_key, resource_version
            )
            values ('lineageweave', 'search-path-publication', 1)
            returning resource_id
            """
        )
        await connection.execute(
            """
            insert into public.ui_translation_key(resource_id, translation_key)
            values ($1, 'label')
            """,
            resource_id,
        )
        await connection.execute(
            """
            insert into public.ui_translation_text(
                resource_id, translation_key, locale, translated_text
            )
            values ($1, 'label', 'en', 'label-en')
            """,
            resource_id,
        )

        await connection.execute(
            """
            create temporary table ui_translation_key (
                resource_id bigint not null,
                translation_key text not null
            );
            create temporary table ui_translation_text (
                translation_text_id bigint generated always as identity,
                resource_id bigint not null,
                translation_key text not null,
                locale text not null,
                translated_text text not null
            );
            """
        )
        await connection.execute(
            "insert into pg_temp.ui_translation_key values ($1, 'label')",
            resource_id,
        )
        await connection.executemany(
            """
            insert into pg_temp.ui_translation_text(
                resource_id, translation_key, locale, translated_text
            )
            values ($1, 'label', $2, $3)
            """,
            [(resource_id, locale, f"spoof-{locale}") for locale in _LOCALES],
        )

        with pytest.raises(
            asyncpg.PostgresError,
            match="incomplete for the eight-locale contract",
        ):
            await connection.execute(
                """
                update public.ui_translation_resource
                   set publication_state = 'published'
                 where resource_id = $1
                """,
                resource_id,
            )

        assert (
            await connection.fetchval(
                "select publication_state from public.ui_translation_resource where resource_id = $1",
                resource_id,
            )
            == "draft"
        )

    asyncio.run(_with_database(scenario))


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_published_child_guard_ignores_pg_temp_resource_shadow() -> None:
    """TEMP root state must not make published permanent child rows mutable."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await _create_complete_resource(connection)
        await connection.execute(
            """
            create temporary table ui_translation_resource (
                resource_id bigint primary key,
                publication_state text not null
            )
            """
        )
        await connection.execute(
            "insert into pg_temp.ui_translation_resource values ($1, 'draft')",
            resource_id,
        )

        with pytest.raises(asyncpg.PostgresError, match="immutable"):
            await connection.execute(
                """
                update public.ui_translation_text
                   set translated_text = 'tampered'
                 where resource_id = $1
                   and translation_key = 'label'
                   and locale = 'en'
                """,
                resource_id,
            )

        assert (
            await connection.fetchval(
                """
                select translated_text
                  from public.ui_translation_text
                 where resource_id = $1
                   and translation_key = 'label'
                   and locale = 'en'
                """,
                resource_id,
            )
            == "label-en"
        )

    asyncio.run(_with_database(scenario))


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_truncate_guard_ignores_pg_temp_resource_shadow() -> None:
    """TEMP root state must not bypass immutable published-copy TRUNCATE guards."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource_id = await _create_complete_resource(connection)
        await connection.execute(
            """
            create temporary table ui_translation_resource (
                resource_id bigint primary key,
                publication_state text not null
            )
            """
        )

        with pytest.raises(asyncpg.PostgresError, match="cannot be truncated"):
            await connection.execute("truncate table public.ui_translation_text")

        assert (
            await connection.fetchval(
                "select count(*) from public.ui_translation_text where resource_id = $1",
                resource_id,
            )
            == len(_LOCALES)
        )

    asyncio.run(_with_database(scenario, include_truncate_guard=True))

"""Customer Master eight-locale translation-seed contract."""

from __future__ import annotations

import asyncio
import os
import re
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
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"
_CUSTOMER_MASTER_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0248_customer_master_translation_draft.sql"
)
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")
_EXPECTED_KEYS = {
    "A counterparty can hold more than one role over time -- a customer in one post can be a competitor, supplier, or partner in another. Every role observed for a name is listed, not just the most frequent.",
    "Affiliates of {name}",
    "Author context",
    "Authorization context",
    "Authorized customer scope",
    "Customer entities available to this account.",
    "Customer master could not be loaded.",
    "Customer master",
    "Hint only",
    "Keymen",
    "Loading customer master...",
    "Loading related posts...",
    "Multiple roles observed",
    "No customer entities are connected to this account.",
    "No linked posts yet.",
    "No post body.",
    "Observed customer evidence",
    "Open record",
    "Open related post: {label}",
    "Our-side Keymen hints",
    "Post body preview",
    "Related posts",
    "Relationship network",
    "Resolve",
    "Resolving...",
    "Retry",
    "Retry needed",
    "Shown as top level: listed parent forms a cycle.",
    "Shown as top level: entity lists itself as parent.",
    "Shown as top level: listed parent is not visible.",
    "This request failed. Retry the same action.",
    "Showing the first {shown} of {total} observed customer identifiers, ranked by post count.",
    "Showing the first {shown} of {total} observed source authors, ranked by post count.",
    "Source identifiers are hints only; ontology and semantic evidence must resolve them before binding a customer.",
    "This hint could not be resolved to a corroborated organization name.",
    "Unresolved source identifier",
    "posts",
}
_PLACEHOLDER = re.compile(r"\{[^{}]+\}")


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


async def _run_with_seed_db(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Apply the ledger and Customer Master seed in an isolated database."""
    database_name = f"lineageweave_customer_copy_{uuid.uuid4().hex[:12]}"
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
                _CUSTOMER_MASTER_SEED,
            ):
                await connection.execute(migration.read_text(encoding="utf-8"))
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_customer_master_seed_is_complete_nonfallback_and_publishable() -> None:
    """The review candidate is complete for all eight locales before publication."""

    async def scenario(connection: asyncpg.Connection) -> None:
        resource = await connection.fetchrow(
            """
            select resource_id, publication_state, published_at
              from ui_translation_resource
             where product_key = 'lineageweave'
               and screen_key = 'customer-master'
               and resource_version = 1
            """
        )
        assert resource is not None
        resource_id = resource["resource_id"]
        assert resource["publication_state"] == "draft"
        assert resource["published_at"] is None

        key_rows = await connection.fetch(
            """
            select translation_key
              from ui_translation_key
             where resource_id = $1
            """,
            resource_id,
        )
        assert {row["translation_key"] for row in key_rows} == _EXPECTED_KEYS

        text_rows = await connection.fetch(
            """
            select translation_key, locale, translated_text
              from ui_translation_text
             where resource_id = $1
            """,
            resource_id,
        )
        assert len(text_rows) == len(_EXPECTED_KEYS) * len(_LOCALES)
        by_key: dict[str, dict[str, str]] = {}
        for row in text_rows:
            by_key.setdefault(row["translation_key"], {})[row["locale"]] = row[
                "translated_text"
            ]

        for translation_key in _EXPECTED_KEYS:
            translations = by_key[translation_key]
            assert set(translations) == set(_LOCALES)
            assert translations["en"] == translation_key
            expected_placeholders = sorted(_PLACEHOLDER.findall(translation_key))
            for locale, translated_text in translations.items():
                assert translated_text.strip()
                assert sorted(_PLACEHOLDER.findall(translated_text)) == expected_placeholders
                if locale != "en":
                    assert translated_text != translation_key

        # Replays must keep one exact draft rather than creating a second version.
        await connection.execute(_CUSTOMER_MASTER_SEED.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'customer-master'
                   and resource_version = 1
                """
            )
            == 1
        )

        # Publication itself is deliberately separate from the seed migration,
        # but the database must accept this exact candidate as complete.
        await connection.execute(
            """
            update ui_translation_resource
               set publication_state = 'published'
             where resource_id = $1
            """,
            resource_id,
        )
        published = await connection.fetchrow(
            """
            select publication_state, published_at
              from ui_translation_resource
             where resource_id = $1
            """,
            resource_id,
        )
        assert published["publication_state"] == "published"
        assert published["published_at"] is not None

    asyncio.run(_run_with_seed_db(scenario))


def test_customer_master_seed_rollback_removes_only_unpublished_draft() -> None:
    """Rollback removes the review draft but refuses a later published resource."""

    async def draft_scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(_CUSTOMER_MASTER_ROLLBACK.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'customer-master'
                   and resource_version = 1
                """
            )
            == 0
        )

    asyncio.run(_run_with_seed_db(draft_scenario))

    async def published_scenario(connection: asyncpg.Connection) -> None:
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
            "update ui_translation_resource set publication_state = 'published' "
            "where resource_id = $1",
            resource_id,
        )
        with pytest.raises(asyncpg.PostgresError, match="refuses to remove published"):
            await connection.execute(
                _CUSTOMER_MASTER_ROLLBACK.read_text(encoding="utf-8")
            )
        # The rollback migration opens its own transaction. A deliberate refusal
        # aborts that transaction, so clear it before asserting durable state.
        await connection.execute("rollback")
        assert (
            await connection.fetchval(
                "select publication_state from ui_translation_resource "
                "where resource_id = $1",
                resource_id,
            )
            == "published"
        )

    asyncio.run(_run_with_seed_db(published_scenario))

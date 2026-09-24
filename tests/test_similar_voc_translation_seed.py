"""Similar VOC eight-locale translation seed and ownership lifecycle contract."""

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
_EXISTING_SEED_OWNERSHIP = (
    ROOT / "migrations" / "0247_z_customer_master_translation_seed_ownership.sql"
)
_GENERIC_SEED_OWNERSHIP = (
    ROOT / "migrations" / "0249_ui_translation_seed_ownership_generic.sql"
)
_SIMILAR_VOC_SEED = ROOT / "migrations" / "0249_z_similar_voc_translation_draft.sql"
_SIMILAR_VOC_ROLLBACK = (
    ROOT / "migrations" / "rollback" / "0249_z_similar_voc_translation_draft.sql"
)
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")
_EXPECTED_KEYS = {
    "Similar VOC · customer cohort",
    "Review prior evidence and action history adjudicated as the same issue type.",
    "The retained evidence remains visible. Retry the failed next page.",
    "Retry the failed next page.",
    "Retry the same query.",
    "Retry loading earlier VOC",
    "Retry Similar VOC",
    "Similar VOC evidence is being adjudicated.",
    "No prior VOC was adjudicated as the same issue type.",
    "Event time {time}",
    "Current post evidence",
    "Prior post evidence",
    "Customer cohort",
    "No same-customer evidence",
    "Prior actions",
    "No recorded action",
    "Open evidence post",
    "Loading earlier VOC...",
    "Show earlier VOC",
    "Retry needed",
    "This request failed. Retry the same action.",
    "Could not load more prior VOC. Try again.",
    "Similar VOC adjudication is unavailable. Try again later.",
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


async def _apply_base(connection: asyncpg.Connection) -> None:
    """Apply the translation-ledger prerequisites shared by every scenario."""
    for migration in (
        _INITIAL_SCHEMA,
        _MEMBER_LOCALE_MIGRATION,
        _LEDGER_MIGRATION,
        _TRUNCATE_GUARD_MIGRATION,
        _EXISTING_SEED_OWNERSHIP,
    ):
        await connection.execute(migration.read_text(encoding="utf-8"))


async def _run_in_database(
    scenario: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Run one seed scenario in an isolated PostgreSQL database."""
    database_name = f"lineageweave_similar_voc_copy_{uuid.uuid4().hex[:12]}"
    admin_connection = await asyncpg.connect(_ADMIN_DSN)
    await admin_connection.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = await asyncpg.connect(database_dsn)
        try:
            await _apply_base(connection)
            await scenario(connection)
        finally:
            await connection.close()
    finally:
        await admin_connection.execute(f'drop database "{database_name}"')
        await admin_connection.close()


def test_similar_voc_seed_is_complete_and_replay_preserves_reviewed_copy() -> None:
    """The draft is eight-locale complete and replay never overwrites review edits."""

    async def scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))

        resource = await connection.fetchrow(
            """
            select resource_id, publication_state, published_at
              from ui_translation_resource
             where product_key = 'lineageweave'
               and screen_key = 'similar-voc'
               and resource_version = 1
            """
        )
        assert resource is not None
        resource_id = resource["resource_id"]
        assert resource["publication_state"] == "draft"
        assert resource["published_at"] is None

        key_rows = await connection.fetch(
            "select translation_key from ui_translation_key where resource_id = $1",
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
            for translated_text in translations.values():
                assert translated_text.strip()
                assert sorted(_PLACEHOLDER.findall(translated_text)) == expected_placeholders

        reviewed_copy = "검토자가 수정한 유사 VOC 제목"
        await connection.execute(
            """
            update ui_translation_text
               set translated_text = $1
             where resource_id = $2
               and translation_key = 'Similar VOC · customer cohort'
               and locale = 'ko'
            """,
            reviewed_copy,
            resource_id,
        )
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select translated_text
                  from ui_translation_text
                 where resource_id = $1
                   and translation_key = 'Similar VOC · customer cohort'
                   and locale = 'ko'
                """,
                resource_id,
            )
            == reviewed_copy
        )
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            == 1
        )

    asyncio.run(_run_in_database(scenario))


def test_similar_voc_seed_refuses_unowned_resource_and_never_resurrects_retired_copy() -> None:
    """The one-time seed neither adopts operator data nor resurrects reviewed deletion."""

    async def collision_scenario(connection: asyncpg.Connection) -> None:
        foreign_resource_id = await connection.fetchval(
            """
            insert into ui_translation_resource(product_key, screen_key, resource_version)
            values ('lineageweave', 'similar-voc', 1)
            returning resource_id
            """
        )
        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        with pytest.raises(asyncpg.PostgresError, match="refuses to adopt"):
            await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        await connection.execute("rollback")
        assert (
            await connection.fetchval(
                "select resource_id from ui_translation_resource where resource_id = $1",
                foreign_resource_id,
            )
            == foreign_resource_id
        )

    asyncio.run(_run_in_database(collision_scenario))

    async def retirement_scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        resource_id = await connection.fetchval(
            """
            select resource_id
              from ui_translation_resource
             where product_key = 'lineageweave'
               and screen_key = 'similar-voc'
               and resource_version = 1
            """
        )
        await connection.execute(
            "delete from ui_translation_resource where resource_id = $1", resource_id
        )
        ownership = await connection.fetchrow(
            """
            select ownership_state, resource_id
              from ui_translation_seed_ownership
             where migration_key = '0249_z_similar_voc_translation_draft'
            """
        )
        assert ownership["ownership_state"] == "retired"
        assert ownership["resource_id"] is None

        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            == 0
        )

    asyncio.run(_run_in_database(retirement_scenario))


def test_similar_voc_explicit_rollback_is_owned_draft_only_and_reseedable() -> None:
    """Explicit rollback removes only the owned draft and intentionally clears its receipt."""

    async def scenario(connection: asyncpg.Connection) -> None:
        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_ROLLBACK.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            == 0
        )
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_seed_ownership
                 where migration_key = '0249_z_similar_voc_translation_draft'
                """
            )
            == 0
        )

        await connection.execute(_GENERIC_SEED_OWNERSHIP.read_text(encoding="utf-8"))
        await connection.execute(_SIMILAR_VOC_SEED.read_text(encoding="utf-8"))
        assert (
            await connection.fetchval(
                """
                select count(*)
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            == 1
        )

        await connection.execute(
            """
            update ui_translation_resource
               set publication_state = 'published'
             where product_key = 'lineageweave'
               and screen_key = 'similar-voc'
               and resource_version = 1
            """
        )
        with pytest.raises(asyncpg.PostgresError, match="refuses to remove published"):
            await connection.execute(_SIMILAR_VOC_ROLLBACK.read_text(encoding="utf-8"))
        await connection.execute("rollback")
        assert (
            await connection.fetchval(
                """
                select publication_state
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
                """
            )
            == "published"
        )

    asyncio.run(_run_in_database(scenario))

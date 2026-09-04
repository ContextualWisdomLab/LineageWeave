"""Concurrency regression for publication versus child-table TRUNCATE."""

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
_TRUNCATE_GUARD_MIGRATION = ROOT / "migrations" / "0247_ui_translation_truncate_guard.sql"
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


async def _seed_complete_draft(connection: asyncpg.Connection) -> int:
    """Create one publishable draft whose text table can be truncated concurrently."""
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
            ) values ($1, 'title', $2, $3)
            """,
            resource_id,
            locale,
            f"title-{locale}",
        )
    return resource_id


async def _wait_until_lock_blocked(observer: asyncpg.Connection, backend_pid: int) -> None:
    """Wait until the publisher is blocked on the child relation lock."""
    for _ in range(100):
        waiting = await observer.fetchval(
            """
            select wait_event_type = 'Lock'
              from pg_stat_activity
             where pid = $1
            """,
            backend_pid,
        )
        if waiting:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("publisher did not block on translation child relation")


async def _run_publication_truncate_race() -> None:
    """Never allow a published root to commit after its copy was truncated."""
    database_name = f"lineageweave_translation_race_{uuid.uuid4().hex[:12]}"
    admin = await asyncpg.connect(_ADMIN_DSN)
    await admin.execute(f'create database "{database_name}"')
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        setup = await asyncpg.connect(database_dsn)
        truncator = await asyncpg.connect(database_dsn)
        publisher = await asyncpg.connect(database_dsn)
        try:
            await setup.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
            await setup.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
            await setup.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            await setup.execute(_TRUNCATE_GUARD_MIGRATION.read_text(encoding="utf-8"))
            resource_id = await _seed_complete_draft(setup)
            publisher_pid = await publisher.fetchval("select pg_backend_pid()")

            truncate_transaction = truncator.transaction()
            await truncate_transaction.start()
            await truncator.execute(
                "lock table ui_translation_text in access exclusive mode"
            )

            async def publish() -> BaseException | None:
                try:
                    await publisher.execute(
                        """
                        update ui_translation_resource
                           set publication_state = 'published'
                         where resource_id = $1
                        """,
                        resource_id,
                    )
                except BaseException as exc:  # preserve the database race outcome for assertions
                    return exc
                return None

            publish_task = asyncio.create_task(publish())
            await _wait_until_lock_blocked(setup, publisher_pid)

            truncate_error: BaseException | None = None
            try:
                await asyncio.wait_for(
                    truncator.execute("truncate table ui_translation_text"), timeout=5
                )
                await truncate_transaction.commit()
            except BaseException as exc:  # deadlock resolution may abort either side
                truncate_error = exc
                try:
                    await truncate_transaction.rollback()
                except asyncpg.PostgresError:
                    pass

            publish_error = await asyncio.wait_for(publish_task, timeout=5)
            publication_state = await setup.fetchval(
                "select publication_state from ui_translation_resource where resource_id = $1",
                resource_id,
            )
            text_count = await setup.fetchval(
                "select count(*) from ui_translation_text where resource_id = $1",
                resource_id,
            )

            assert not (publication_state == "published" and text_count == 0), (
                "publication committed from a stale command snapshot after child TRUNCATE"
            )
            assert truncate_error is not None or publish_error is not None, (
                "the conflicting publication/TRUNCATE pair was not serialized"
            )
        finally:
            await publisher.close()
            await truncator.close()
            await setup.close()
    finally:
        await admin.execute(f'drop database "{database_name}"')
        await admin.close()


@pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)
def test_postgres_publication_cannot_commit_after_child_truncate() -> None:
    """Cross-table immutability remains true under the READ COMMITTED race."""
    asyncio.run(_run_publication_truncate_race())

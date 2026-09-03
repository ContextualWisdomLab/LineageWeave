"""Real-PostgreSQL verification for the versioned UI translation ledger."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest


ROOT = Path(__file__).resolve().parents[1]
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_INITIAL_SCHEMA = ROOT / "migrations" / "0001_initial_schema.sql"
_MEMBER_LOCALE_MIGRATION = ROOT / "migrations" / "0044_member_locale_preference.sql"
_TRANSLATION_LEDGER_MIGRATION = ROOT / "migrations" / "0246_ui_translation_ledger.sql"
_LOCALES = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")


def _postgres_available() -> bool:
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


@pytest.fixture
def translation_db():
    """Apply the real prerequisite and ledger migrations to a throwaway database."""
    database_name = f"lineageweave_translation_test_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')

    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    database_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))
    try:
        connection = psycopg2.connect(database_dsn)
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                cursor.execute(_MEMBER_LOCALE_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_TRANSLATION_LEDGER_MIGRATION.read_text(encoding="utf-8"))
            connection.autocommit = False
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin_connection.close()


def _seed_complete_draft(connection, *, version: int = 1) -> int:
    """Create one synthetic complete eight-locale draft and return its resource id."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into ui_translation_resource(product_key, screen_key, resource_version)
            values ('lineageweave', 'customer-master', %s)
            returning resource_id
            """,
            (version,),
        )
        resource_id = cursor.fetchone()[0]
        cursor.execute(
            """
            insert into ui_translation_key(resource_id, translation_key)
            values (%s, 'title')
            """,
            (resource_id,),
        )
        for locale in _LOCALES:
            cursor.execute(
                """
                insert into ui_translation_text(
                    resource_id,
                    translation_key,
                    locale,
                    translated_text
                )
                values (%s, 'title', %s, %s)
                """,
                (resource_id, locale, f"title-{locale}"),
            )
    return resource_id


def test_postgres_rejects_padded_translation_resource_identity(translation_db) -> None:
    """Database aggregate identity cannot diverge from reader/cache canonicalization."""
    for product_key, screen_key in (
        ("lineageweave ", "customer-master"),
        ("lineageweave", " customer-master"),
    ):
        with pytest.raises(psycopg2.errors.CheckViolation):
            with translation_db.cursor() as cursor:
                cursor.execute(
                    """
                    insert into ui_translation_resource(product_key, screen_key, resource_version)
                    values (%s, %s, 1)
                    """,
                    (product_key, screen_key),
                )
        translation_db.rollback()


def test_postgres_publication_timestamp_is_database_owned(translation_db) -> None:
    """Caller input cannot forge the immutable publication-time receipt."""
    resource_id = _seed_complete_draft(translation_db)
    with translation_db.cursor() as cursor:
        cursor.execute(
            """
            update ui_translation_resource
               set publication_state = 'published',
                   published_at = timestamptz '2000-01-01 00:00:00+00'
             where resource_id = %s
         returning published_at = transaction_timestamp()
            """,
            (resource_id,),
        )
        assert cursor.fetchone()[0] is True

    with pytest.raises(psycopg2.errors.RaiseException, match="immutable"):
        with translation_db.cursor() as cursor:
            cursor.execute(
                "update ui_translation_resource set published_at = now() where resource_id = %s",
                (resource_id,),
            )
    translation_db.rollback()


def test_postgres_publication_fails_closed_when_one_locale_is_missing(translation_db) -> None:
    """The database itself rejects an incomplete required-key × locale matrix."""
    with translation_db.cursor() as cursor:
        cursor.execute(
            """
            insert into ui_translation_resource(product_key, screen_key, resource_version)
            values ('lineageweave', 'customer-master', 2)
            returning resource_id
            """
        )
        resource_id = cursor.fetchone()[0]
        cursor.execute(
            "insert into ui_translation_key(resource_id, translation_key) values (%s, 'title')",
            (resource_id,),
        )
        for locale in _LOCALES[:-1]:
            cursor.execute(
                """
                insert into ui_translation_text(
                    resource_id,
                    translation_key,
                    locale,
                    translated_text
                )
                values (%s, 'title', %s, %s)
                """,
                (resource_id, locale, f"title-{locale}"),
            )

    with pytest.raises(psycopg2.errors.RaiseException, match="incomplete"):
        with translation_db.cursor() as cursor:
            cursor.execute(
                "update ui_translation_resource set publication_state = 'published' where resource_id = %s",
                (resource_id,),
            )
    translation_db.rollback()

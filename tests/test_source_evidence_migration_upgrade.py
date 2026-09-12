"""Real-PostgreSQL upgrade/replay tests for canonical source-evidence migration identity."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

psycopg2 = pytest.importorskip("psycopg2")
sql = pytest.importorskip("psycopg2.sql")

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS = _ROOT / "migrations"
_PRE_0233_MIGRATIONS = (
    _MIGRATIONS / "0001_initial_schema.sql",
    _MIGRATIONS / "0026_post_content_artifacts.sql",
)
_HISTORICAL_FORWARD = _MIGRATIONS / "0233_source_conversation_turn_evidence.sql"
_CANONICAL_FORWARD = _MIGRATIONS / "0248_source_conversation_turn_evidence.sql"
_HISTORICAL_ROLLBACK = _MIGRATIONS / "rollback" / "0233_source_conversation_turn_evidence.sql"
_CANONICAL_ROLLBACK = _MIGRATIONS / "rollback" / "0248_source_conversation_turn_evidence.sql"
_CONSTRAINT = "post_content_unit_source_evidence_reference_check"


def _postgres_available() -> bool:
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


def _dsn_for_database(admin_dsn: str, database_name: str) -> str:
    parsed_admin_dsn = urlsplit(admin_dsn)
    return urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))


def _apply_migration(connection, migration_path: Path) -> None:
    """Run one migration with the SQL file owning its own transaction boundary."""
    with connection.cursor() as cursor:
        cursor.execute(migration_path.read_text(encoding="utf-8"))


def _source_evidence_shape(connection) -> tuple[int, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)
              from information_schema.columns
             where table_schema = 'public'
               and table_name = 'post_content_unit'
               and column_name = 'source_evidence_reference'
            """
        )
        column_count = cursor.fetchone()[0]
        cursor.execute(
            """
            select count(*)
              from pg_constraint
             where conname = %s
               and conrelid = 'post_content_unit'::regclass
            """,
            (_CONSTRAINT,),
        )
        constraint_count = cursor.fetchone()[0]
    return column_count, constraint_count


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def pre_0233_database():
    """Yield a database with the target table present but no source-evidence migration."""
    database_name = f"lineageweave_source_evidence_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    try:
        database_connection = psycopg2.connect(_dsn_for_database(_ADMIN_DSN, database_name))
        # Migration files contain BEGIN/COMMIT. Keep the driver out of an implicit
        # transaction so the migration owns exactly one transaction boundary.
        database_connection.autocommit = True
        try:
            for migration_path in _PRE_0233_MIGRATIONS:
                _apply_migration(database_connection, migration_path)
            assert _source_evidence_shape(database_connection) == (0, 0)
            yield database_connection
        finally:
            database_connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin_connection.close()


def test_canonical_upgrade_replays_after_historical_0233(pre_0233_database) -> None:
    """An old volume can see historical 0233, then canonical 0248 repeatedly."""
    _apply_migration(pre_0233_database, _HISTORICAL_FORWARD)
    assert _source_evidence_shape(pre_0233_database) == (1, 1)

    _apply_migration(pre_0233_database, _CANONICAL_FORWARD)
    _apply_migration(pre_0233_database, _CANONICAL_FORWARD)

    assert _source_evidence_shape(pre_0233_database) == (1, 1)


def test_historical_and_canonical_rollbacks_have_equivalent_effect(pre_0233_database) -> None:
    """Both discoverable rollback paths remove the canonical schema effect."""
    _apply_migration(pre_0233_database, _CANONICAL_FORWARD)
    assert _source_evidence_shape(pre_0233_database) == (1, 1)

    _apply_migration(pre_0233_database, _HISTORICAL_ROLLBACK)
    assert _source_evidence_shape(pre_0233_database) == (0, 0)

    _apply_migration(pre_0233_database, _CANONICAL_FORWARD)
    _apply_migration(pre_0233_database, _CANONICAL_ROLLBACK)
    assert _source_evidence_shape(pre_0233_database) == (0, 0)

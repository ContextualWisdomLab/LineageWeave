"""Real-PostgreSQL upgrade/replay tests for canonical source-evidence migration identity."""

from __future__ import annotations

import os
import subprocess
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
    _MIGRATIONS / "0012_report_leftover_pair.sql",
    _MIGRATIONS / "0026_post_content_artifacts.sql",
)
_REPORT_FORWARD = _MIGRATIONS / "0233_report_leftover_map_unexplained_share.sql"
_HISTORICAL_FORWARD = _MIGRATIONS / "0233_source_conversation_turn_evidence.sql"
_CANONICAL_FORWARD = _MIGRATIONS / "0248_source_conversation_turn_evidence.sql"
_HISTORICAL_ROLLBACK = _MIGRATIONS / "rollback" / "0233_source_conversation_turn_evidence.sql"
_CANONICAL_ROLLBACK = _MIGRATIONS / "rollback" / "0248_source_conversation_turn_evidence.sql"
_MIGRATE_SCRIPT = _ROOT / "docker" / "postgres-init" / "migrate.sh"
_CONSTRAINT = "post_content_unit_source_evidence_reference_check"


def _postgres_available() -> bool:
    """Return whether the configured PostgreSQL admin endpoint is reachable."""
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


def _dsn_for_database(admin_dsn: str, database_name: str) -> str:
    """Replace only the database path in the configured URI-style admin DSN."""
    parsed_admin_dsn = urlsplit(admin_dsn)
    return urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))


def _apply_migration(connection, migration_path: Path) -> None:
    """Run one migration with the SQL file owning its own transaction boundary."""
    with connection.cursor() as cursor:
        cursor.execute(migration_path.read_text(encoding="utf-8"))


def _column_count(connection, table_name: str, column_name: str) -> int:
    """Return one table column's schema cardinality without interpolating identifiers."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)
              from information_schema.columns
             where table_schema = 'public'
               and table_name = %s
               and column_name = %s
            """,
            (table_name, column_name),
        )
        return int(cursor.fetchone()[0])


def _source_evidence_shape(connection) -> tuple[int, int]:
    """Return source-evidence column and named-constraint cardinalities."""
    column_count = _column_count(
        connection,
        "post_content_unit",
        "source_evidence_reference",
    )
    with connection.cursor() as cursor:
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


def _migrate_script_environment(connection) -> dict[str, str]:
    """Build the production replay script environment for the throwaway database."""
    params = connection.get_dsn_parameters()
    parsed_admin_dsn = urlsplit(_ADMIN_DSN)
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_HOST": params.get("host") or "localhost",
            "POSTGRES_PORT": params.get("port") or "5432",
            "POSTGRES_USER": params.get("user") or parsed_admin_dsn.username or "postgres",
            "POSTGRES_PASSWORD": (
                parsed_admin_dsn.password or os.environ.get("PGPASSWORD") or "unused"
            ),
            "POSTGRES_DB": params["dbname"],
        }
    )
    return environment


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def pre_0233_database():
    """Yield a database with both affected tables but neither collided 0233 delta."""
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
            assert (
                _column_count(
                    database_connection,
                    "report_leftover_pair",
                    "leftover_map_unexplained_share",
                )
                == 0
            )
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


def test_production_replay_skips_alias_and_preserves_both_0233_deltas(
    pre_0233_database, tmp_path: Path
) -> None:
    """The exact production replay loop applies both real deltas on repeated runs."""
    migration_root = tmp_path / "migrations"
    migration_root.mkdir()
    for migration_path in (_REPORT_FORWARD, _HISTORICAL_FORWARD, _CANONICAL_FORWARD):
        (migration_root / migration_path.name).write_bytes(migration_path.read_bytes())

    environment = _migrate_script_environment(pre_0233_database)
    runs = [
        subprocess.run(
            ["sh", str(_MIGRATE_SCRIPT), str(migration_root)],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        for _ in range(2)
    ]

    for run in runs:
        assert "Applying 0233_report_leftover_map_unexplained_share.sql" in run.stdout
        assert "Skipping compatibility alias 0233_source_conversation_turn_evidence.sql" in run.stdout
        assert "Applying 0248_source_conversation_turn_evidence.sql" in run.stdout

    assert (
        _column_count(
            pre_0233_database,
            "report_leftover_pair",
            "leftover_map_unexplained_share",
        )
        == 1
    )
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

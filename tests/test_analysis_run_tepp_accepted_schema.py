"""Static and optional PostgreSQL contracts for TEPP accepted evidence."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_TEPP_RESULT_MIGRATION = _ROOT / "migrations" / "0028_analysis_run_tepp_result.sql"
_TEPP_ACCEPTED_MIGRATION = _ROOT / "migrations" / "0029_analysis_run_tepp_accepted.sql"
_TEPP_ACCEPTED_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0029_analysis_run_tepp_accepted.sql"
)
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_REQUIRED_TABLES = {"analysis_run_tepp_accepted"}


def test_tepp_accepted_migration_is_normalized_and_wired() -> None:
    """Static contract: 3NF names, additive to 0028, Dockerfile copy, rollback."""
    migration = _TEPP_ACCEPTED_MIGRATION.read_text(encoding="utf-8")
    rollback = _TEPP_ACCEPTED_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    seed = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    created_tables = set(
        re.findall(r"create table if not exists\s+([a-z0-9_]+)", migration, re.I)
    )
    assert _REQUIRED_TABLES <= created_tables
    assert "jsonb" not in migration.casefold()
    assert "metadata_payload" not in migration
    assert "theta" not in migration.casefold()
    assert "affiliation_count" not in migration
    assert "interval_count" not in migration
    assert "validated multilevel estimate" in migration
    assert "0029_analysis_run_tepp_accepted.sql" in dockerfile
    assert "0029_analysis_run_tepp_accepted.sql" in seed
    assert seed.index("0028_analysis_run_tepp_result.sql") < seed.index(
        "0029_analysis_run_tepp_accepted.sql"
    )
    assert "analysis_run_tepp_accepted_not_empty" in rollback
    assert "drop table if exists analysis_run_tepp_result" not in rollback
    assert "reject_analysis_run_tepp_accepted_update" in migration
    assert "delete from analysis_run_tepp_accepted" in migration
    assert migration.index("delete from analysis_run_tepp_accepted") < (
        migration.index("delete from analysis_run_status_event")
    )
    for object_name in re.findall(
        r"create table if not exists\s+([a-z0-9_]+)",
        migration,
        re.I,
    ):
        assert len(object_name.split("_")) >= 2, object_name
    for object_name in re.findall(
        r"create or replace function\s+([a-z0-9_]+)",
        migration,
    ):
        assert len(object_name.split("_")) >= 2, object_name
    for object_name in re.findall(r"create trigger\s+([a-z0-9_]+)", migration, re.I):
        assert len(object_name.split("_")) >= 2, object_name


def test_tepp_accepted_migration_is_idempotent_sql() -> None:
    """Upgrade-safe: create if not exists and replace, never drop 0028."""
    migration = _TEPP_ACCEPTED_MIGRATION.read_text(encoding="utf-8")
    assert "create table if not exists analysis_run_tepp_accepted" in migration
    assert "create or replace function purge_analysis_run_registry" in migration
    assert "drop table" not in migration.casefold()
    assert "analysis_run_tepp_result" in migration


def _postgres_available() -> bool:
    """Return whether the configured administrator DSN is reachable."""
    try:
        import psycopg2

        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except Exception:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN query options."""
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def tepp_accepted_db():
    """Yield a throwaway registry plus TEPP-accepted database."""
    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    import psycopg2

    database_name = f"lineageweave_tepp_acc_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(f'create database "{database_name}"')
    finally:
        admin.close()
    conn = psycopg2.connect(_database_dsn(database_name))
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_TEPP_RESULT_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_TEPP_ACCEPTED_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_TEPP_ACCEPTED_MIGRATION.read_text(encoding="utf-8"))
        yield conn
    finally:
        conn.close()
        admin = psycopg2.connect(_ADMIN_DSN)
        admin.autocommit = True
        try:
            with admin.cursor() as cursor:
                cursor.execute(
                    "select pg_terminate_backend(pid) from pg_stat_activity "
                    "where datname = %s and pid <> pg_backend_pid()",
                    (database_name,),
                )
                cursor.execute(f'drop database "{database_name}"')
        finally:
            admin.close()


def test_empty_tepp_accepted_rollback_is_replayable(tepp_accepted_db) -> None:
    """An empty accepted-evidence schema can be rolled back twice."""
    with tepp_accepted_db.cursor() as cursor:
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name = any(%s)",
            (list(_REQUIRED_TABLES | {"analysis_run_tepp_result"}),),
        )
        present = {row[0] for row in cursor.fetchall()}
        assert _REQUIRED_TABLES <= present
        assert "analysis_run_tepp_result" in present
        cursor.execute(_TEPP_ACCEPTED_ROLLBACK.read_text(encoding="utf-8"))
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name = any(%s)",
            (list(_REQUIRED_TABLES | {"analysis_run_tepp_result"}),),
        )
        remaining = {row[0] for row in cursor.fetchall()}
        assert remaining == {"analysis_run_tepp_result"}
        cursor.execute(_TEPP_ACCEPTED_ROLLBACK.read_text(encoding="utf-8"))

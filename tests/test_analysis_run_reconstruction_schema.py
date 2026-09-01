"""Static and optional PostgreSQL contracts for run-scoped reconstruction."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lineageweave import postgres_sync as sync_postgres
from lineageweave.postgres_sync import sql

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_RECONSTRUCTION_MIGRATION = _ROOT / "migrations" / "0021_analysis_run_reconstruction.sql"
_RECONSTRUCTION_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0021_analysis_run_reconstruction.sql"
)
_SNAPSHOT_MEMBER_MIGRATION = (
    _ROOT / "migrations" / "0022_analysis_source_snapshot_member.sql"
)
_SNAPSHOT_MEMBER_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0022_analysis_source_snapshot_member.sql"
)
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_REQUIRED_TABLES = {
    "analysis_run_reconstruction",
    "analysis_run_lineage_edge",
}


def test_reconstruction_migration_is_normalized_and_wired() -> None:
    """Static contract: 3NF names, no payload JSON, Dockerfile copy, rollback."""
    migration = _RECONSTRUCTION_MIGRATION.read_text(encoding="utf-8")
    rollback = _RECONSTRUCTION_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    created_tables = set(
        re.findall(r"create table if not exists\s+([a-z0-9_]+)", migration, re.I)
    )
    assert _REQUIRED_TABLES <= created_tables
    assert "jsonb" not in migration.casefold()
    assert "metadata_payload" not in migration
    assert "theta" not in migration.casefold()
    assert "0021_analysis_run_reconstruction.sql" in dockerfile
    assert "0022_analysis_source_snapshot_member.sql" in dockerfile
    assert "0023_analysis_run_outbox.sql" in dockerfile
    assert "0024_source_post_revision.sql" in dockerfile
    assert "0025_role_person_catalog_identity.sql" in dockerfile
    assert "analysis_run_reconstruction_not_empty" in rollback
    assert "reject_analysis_run_reconstruction_update" in migration
    assert "reject_analysis_run_lineage_edge_update" in migration
    member_migration = _SNAPSHOT_MEMBER_MIGRATION.read_text(encoding="utf-8")
    member_rollback = _SNAPSHOT_MEMBER_ROLLBACK.read_text(encoding="utf-8")
    assert "analysis_source_snapshot_member" in member_migration
    assert "jsonb" not in member_migration.casefold()
    assert "theta" not in member_migration.casefold()
    assert "analysis_source_snapshot_member_not_empty" in member_rollback
    assert "reject_analysis_source_snapshot_member_update" in member_migration
    for object_name in re.findall(
        r"create table if not exists\s+([a-z0-9_]+)",
        member_migration,
        re.I,
    ):
        assert len(object_name.split("_")) >= 2, object_name

    object_patterns = (
        r"create table if not exists\s+([a-z0-9_]+)",
        r"create or replace function\s+([a-z0-9_]+)",
        r"create trigger\s+([a-z0-9_]+)",
    )
    for pattern in object_patterns:
        for object_name in re.findall(pattern, migration, re.I):
            assert len(object_name.split("_")) >= 2, object_name


def _postgres_available() -> bool:
    """Return whether the configured administrator DSN is reachable."""
    try:
        sync_postgres.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except sync_postgres.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN query options."""
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def reconstruction_db():
    """Yield a throwaway registry+reconstruction database."""
    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")

    database_name = f"lineageweave_recon_{uuid.uuid4().hex[:12]}"
    admin = sync_postgres.connect(_ADMIN_DSN)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL("create database {}").format(sql.Identifier(database_name))
            )
    finally:
        admin.close()
    conn = sync_postgres.connect(_database_dsn(database_name))
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_RECONSTRUCTION_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_SNAPSHOT_MEMBER_MIGRATION.read_text(encoding="utf-8"))
        yield conn
    finally:
        conn.close()
        admin = sync_postgres.connect(_ADMIN_DSN)
        admin.autocommit = True
        try:
            with admin.cursor() as cursor:
                cursor.execute(
                    "select pg_terminate_backend(pid) from pg_stat_activity "
                    "where datname = %s and pid <> pg_backend_pid()",
                    (database_name,),
                )
                cursor.execute(
                    sql.SQL("drop database {}").format(sql.Identifier(database_name))
                )
        finally:
            admin.close()


def test_empty_reconstruction_rollback_is_replayable(reconstruction_db) -> None:
    """An empty reconstruction schema can be rolled back and removed."""
    with reconstruction_db.cursor() as cursor:
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name = any(%s)",
            (list(_REQUIRED_TABLES),),
        )
        assert {row[0] for row in cursor.fetchall()} == _REQUIRED_TABLES
        cursor.execute(_RECONSTRUCTION_ROLLBACK.read_text(encoding="utf-8"))
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name = any(%s)",
            (list(_REQUIRED_TABLES),),
        )
        assert cursor.fetchall() == []
        cursor.execute(_RECONSTRUCTION_ROLLBACK.read_text(encoding="utf-8"))

"""Regression contracts for immutable analysis authorization scopes."""

from __future__ import annotations

import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest

try:
    import psycopg2
    import psycopg2.errors
    from psycopg2 import sql
except ModuleNotFoundError:  # pragma: no cover - local static-only environments
    psycopg2 = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_SCOPE_MIGRATION = _ROOT / "migrations" / "0019_analysis_run_scope_immutability.sql"
_SCOPE_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0019_analysis_run_scope_immutability.sql"
)
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)


def _postgres_available() -> bool:
    """Return whether the configured PostgreSQL administrator DSN is reachable."""

    if psycopg2 is None:
        return False
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while retaining connection options."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def test_scope_hardening_migration_is_wired_and_reversible() -> None:
    """Fresh installs and downgrades must include the scope-mutation contract."""

    assert _SCOPE_MIGRATION.exists()
    assert _SCOPE_ROLLBACK.exists()
    migration = _SCOPE_MIGRATION.read_text(encoding="utf-8")
    rollback = _SCOPE_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    assert "before update or delete on analysis_run_scope" in migration.casefold()
    assert "analysis_run_scope_is_immutable" in migration
    assert "reject_analysis_run_scope_mutation" in migration
    assert "reject_analysis_run_scope_update" in rollback
    assert "0019_analysis_run_scope_immutability.sql" in dockerfile


@pytest.fixture
def scope_database():
    """Yield a disposable database migrated through scope hardening."""

    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    assert psycopg2 is not None
    assert sql is not None
    database_name = f"lineageweave_scope_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    try:
        connection = psycopg2.connect(_database_dsn(database_name))
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SCOPE_MIGRATION.read_text(encoding="utf-8"))
            yield connection
        finally:
            connection.close()
    finally:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin.close()


def test_scope_cannot_be_updated_or_deleted_after_registration(scope_database) -> None:
    """A persisted run cannot lose or rewrite its authorization boundary."""

    assert psycopg2 is not None
    with scope_database.cursor() as cursor:
        suffix = uuid.uuid4().hex
        cursor.execute(
            """
            insert into user_account
                (external_subject_id, display_name, email_address)
            values (%s, 'Scope Operator', %s)
            returning user_account_id
            """,
            (f"scope-{suffix}", f"scope-{suffix}@example.test"),
        )
        account_id = cursor.fetchone()[0]
        cursor.execute(
            """
            insert into analysis_source_snapshot
                (snapshot_sha256, source_contract_version,
                 maximum_available_time, captured_at)
            values (%s, 'source-contract-v1',
                    '2026-08-15T00:00:00Z', '2026-08-15T00:05:00Z')
            returning analysis_source_snapshot_id
            """,
            ("a" * 64,),
        )
        snapshot_id = cursor.fetchone()[0]
        cursor.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha)
            values (%s, 'analysis_run_lineage', 'scope-immutable', %s,
                    '2026-08-15T00:30:00Z', 'lineage-run-v1', %s, %s)
            returning analysis_run_id
            """,
            (snapshot_id, account_id, "b" * 64, "c" * 40),
        )
        run_id = cursor.fetchone()[0]
        cursor.execute(
            """
            insert into analysis_run_scope (analysis_run_id, scope_kind_code)
            values (%s, 'analysis_scope_all_visible')
            """,
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                update analysis_run_scope
                   set scope_kind_code = 'analysis_scope_thread_group',
                       scope_key = 'synthetic-thread'
                 where analysis_run_id = %s
                """,
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run_scope where analysis_run_id = %s",
                (run_id,),
            )
        cursor.execute(
            "select scope_kind_code from analysis_run_scope where analysis_run_id = %s",
            (run_id,),
        )
        assert cursor.fetchone() == ("analysis_scope_all_visible",)

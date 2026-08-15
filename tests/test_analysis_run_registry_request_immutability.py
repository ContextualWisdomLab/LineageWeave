"""Request immutability and transient-artifact contracts for analysis runs."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
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
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_TRANSIENT_PATHS = (
    _ROOT / ".github" / "workflows" / "pr83-analysis-run-registry-repair.yml",
    _ROOT / ".github" / "workflows" / "pr83-analysis-run-registry-repair-v2.yml",
    _ROOT / ".github" / "workflows" / "pr83-analysis-run-registry-repair-v3.yml",
    _ROOT / "scripts" / "pr83_analysis_run_registry_repair.py",
)


def _postgres_available() -> bool:
    """Return whether the configured PostgreSQL administrator is reachable."""

    if psycopg2 is None:
        return False
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Return the configured DSN with only its database path replaced."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def immutable_run_db():
    """Yield a throwaway database migrated through the registry schema."""

    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    assert psycopg2 is not None
    assert sql is not None
    database_name = f"lineageweave_run_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(database_name))
        )
    try:
        connection = psycopg2.connect(_database_dsn(database_name))
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
        admin_connection.close()


def _insert_run(cursor) -> str:
    """Insert one account, source snapshot, and analysis request."""

    suffix = uuid.uuid4().hex
    cursor.execute(
        """
        insert into user_account
            (external_subject_id, display_name, email_address)
        values (%s, 'Registry Operator', %s)
        returning user_account_id
        """,
        (f"registry-{suffix}", f"registry-{suffix}@example.test"),
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
        values (%s, 'analysis_run_lineage', 'immutable-request', %s,
                '2026-08-15T00:30:00Z', 'lineage-run-v1', %s, %s)
        returning analysis_run_id
        """,
        (snapshot_id, account_id, "b" * 64, "c" * 40),
    )
    return str(cursor.fetchone()[0])


def test_transient_repair_artifacts_are_absent_from_the_product_diff() -> None:
    """The final product change contains no one-shot mutation machinery."""

    assert all(not path.exists() for path in _TRANSIENT_PATHS)


def test_analysis_run_request_rejects_update_and_delete(immutable_run_db) -> None:
    """A registered request remains stable for its full provenance lifetime."""

    assert psycopg2 is not None
    with immutable_run_db.cursor() as cursor:
        run_id = _insert_run(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                update analysis_run
                   set knowledge_cutoff = '2026-08-16T00:00:00Z'
                 where analysis_run_id = %s
                """,
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run where analysis_run_id = %s",
                (run_id,),
            )

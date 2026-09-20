"""SQL authorization for the Milestone 2 analysis-run read projection."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lineageweave import postgres_sync as sync_postgres
from lineageweave.postgres_sync import sql
from backend.app.analysis_run_ingestion import (
    _COUNTS_BY_RUN_SQL,
    _RUN_DETAIL_SQL,
    _RUN_LIST_SQL,
)

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_RETENTION_MIGRATION = _ROOT / "migrations" / "0020_analysis_run_retention_purge.sql"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)


def test_visible_run_sql_is_parameterized_literals() -> None:
    """List and detail queries bind $1/$2/$3; they do not format user SQL."""
    assert "$1" in _RUN_LIST_SQL
    assert "$2" in _RUN_LIST_SQL
    assert "$3" in _RUN_DETAIL_SQL
    assert "{" not in _RUN_LIST_SQL
    assert "{" not in _RUN_DETAIL_SQL
    assert "$1" in _COUNTS_BY_RUN_SQL
    assert "{" not in _COUNTS_BY_RUN_SQL


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
def authz_db():
    """Yield a throwaway database migrated through the registry schema."""
    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    database_name = f"lineageweave_authz_{uuid.uuid4().hex[:12]}"
    admin_connection = sync_postgres.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(database_name))
        )
    try:
        connection = sync_postgres.connect(_database_dsn(database_name))
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_RETENTION_MIGRATION.read_text(encoding="utf-8"))
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
        admin_connection.close()


def _insert_account(cursor, label: str) -> str:
    """Insert one synthetic authenticated account and return its UUID."""
    suffix = uuid.uuid4().hex
    cursor.execute(
        """
        insert into user_account
            (external_subject_id, display_name, email_address)
        values (%s, %s, %s)
        returning user_account_id
        """,
        (f"{label}-{suffix}", f"{label.title()} User", f"{label}-{suffix}@example.test"),
    )
    return str(cursor.fetchone()[0])


def _insert_corp(cursor, code: str, name: str) -> str:
    """Insert one synthetic corporate entity."""
    cursor.execute(
        """
        insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
        values ('corporate_entity_level', 'company', 'Company')
        on conflict (lookup_code) do nothing
        """
    )
    cursor.execute(
        """
        insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code)
        values (%s, %s, 'company')
        returning corporate_entity_id
        """,
        (code, name),
    )
    return str(cursor.fetchone()[0])


def _complete_run(
    cursor,
    *,
    account_id: str,
    digest: str,
    idempotency_key: str,
    scope_kind: str,
    corporate_entity_id: str | None = None,
) -> str:
    """Insert one succeeded run with one document-count aggregate."""
    cursor.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, 'source-contract-v1',
                '2026-01-12T00:00:00Z', '2026-01-12T00:05:00Z')
        returning analysis_source_snapshot_id
        """,
        (digest,),
    )
    snapshot_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into analysis_source_count
            (analysis_source_snapshot_id, count_type_code, count_value)
        values (%s, 'analysis_count_document', 3)
        """,
        (snapshot_id,),
    )
    cursor.execute(
        """
        insert into analysis_run
            (analysis_source_snapshot_id, run_kind_code, idempotency_key,
             requested_by_account_id, knowledge_cutoff,
             configuration_schema_version, configuration_sha256,
             code_revision_sha, requested_at)
        values (%s, 'analysis_run_lineage', %s, %s,
                '2026-01-12T12:00:00Z', 'lineage-run-v1', %s, %s,
                '2026-01-12T12:30:00Z')
        returning analysis_run_id
        """,
        (snapshot_id, idempotency_key, account_id, "b" * 64, "c" * 40),
    )
    run_id = str(cursor.fetchone()[0])
    if scope_kind == "analysis_scope_corporate_entity":
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code, corporate_entity_id)
            values (%s, %s, %s)
            """,
            (run_id, scope_kind, corporate_entity_id),
        )
    else:
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code)
            values (%s, %s)
            """,
            (run_id, scope_kind),
        )
    for ordinal, status, occurred in (
        (1, "analysis_status_pending", "2026-01-12T12:31:00Z"),
        (2, "analysis_status_running", "2026-01-12T12:32:00Z"),
        (3, "analysis_status_succeeded", "2026-01-12T12:33:00Z"),
    ):
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, %s, %s, %s)
            """,
            (run_id, ordinal, status, occurred),
        )
    return run_id


def _visible_ids(cursor, account_id: str, entity_ids: list[str]) -> set[str]:
    """Apply the same visibility predicate the product API uses."""
    cursor.execute(
        """
        select run.analysis_run_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        where
          run.requested_by_account_id = %s
          or (
            scope.scope_kind_code = 'analysis_scope_corporate_entity'
            and scope.corporate_entity_id = any(%s::uuid[])
          )
          or (
            scope.scope_kind_code = 'analysis_scope_process_unit'
            and exists (
              select 1 from account_affiliation aff
              where aff.user_account_id = %s
                and aff.process_unit_id = scope.process_unit_id
            )
          )
        """,
        (account_id, entity_ids, account_id),
    )
    return {str(row[0]) for row in cursor.fetchall()}


def test_hidden_scope_does_not_leak_through_all_visible_or_other_corp(authz_db) -> None:
    """A Demo-Corp viewer never sees another tenant's run or its aggregates."""
    with authz_db.cursor() as cursor:
        viewer = _insert_account(cursor, "viewer")
        outsider = _insert_account(cursor, "outsider")
        own_corp = _insert_corp(cursor, "DEMO-CORP-AUTHZ", "Demo Corp")
        other_corp = _insert_corp(cursor, "OTHER-CORP-AUTHZ", "Other Corp")
        cursor.execute(
            """
            insert into account_affiliation (user_account_id, corporate_entity_id)
            values (%s, %s)
            """,
            (viewer, own_corp),
        )
        own_run = _complete_run(
            cursor,
            account_id=viewer,
            digest="a" * 64,
            idempotency_key="own-corp",
            scope_kind="analysis_scope_corporate_entity",
            corporate_entity_id=own_corp,
        )
        hidden_all_visible = _complete_run(
            cursor,
            account_id=outsider,
            digest="d" * 64,
            idempotency_key="hidden-all",
            scope_kind="analysis_scope_all_visible",
        )
        hidden_other_corp = _complete_run(
            cursor,
            account_id=outsider,
            digest="e" * 64,
            idempotency_key="hidden-other",
            scope_kind="analysis_scope_corporate_entity",
            corporate_entity_id=other_corp,
        )

        visible = _visible_ids(cursor, viewer, [own_corp])
        assert own_run in visible
        assert hidden_all_visible not in visible
        assert hidden_other_corp not in visible

        outsider_visible = _visible_ids(cursor, outsider, [other_corp])
        assert hidden_all_visible in outsider_visible
        assert hidden_other_corp in outsider_visible
        assert own_run not in outsider_visible

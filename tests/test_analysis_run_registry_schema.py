"""Real-PostgreSQL contracts for the normalized Milestone 2 run registry."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest
from psycopg2 import sql

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_REGISTRY_ROLLBACK = _ROOT / "migrations" / "rollback" / "0018_analysis_run_registry.sql"
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_REQUIRED_TABLES = {
    "analysis_source_snapshot",
    "analysis_source_count",
    "analysis_run",
    "analysis_run_scope",
    "analysis_run_status_event",
}
_REQUIRED_LOOKUP_CODES = {
    "analysis_run_lineage",
    "analysis_run_report",
    "analysis_run_tepp",
    "analysis_status_pending",
    "analysis_status_running",
    "analysis_status_succeeded",
    "analysis_status_failed",
    "analysis_status_cancelled",
    "analysis_scope_all_visible",
    "analysis_scope_corporate_entity",
    "analysis_scope_process_unit",
    "analysis_scope_thread_group",
    "analysis_count_source_row",
    "analysis_count_document",
    "analysis_count_thread",
    "analysis_count_lineage_node",
    "analysis_count_lineage_edge",
}


def _postgres_available() -> bool:
    """Return whether the configured administrator DSN is reachable."""

    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN query options."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _table_definition(migration: str, table_name: str) -> str:
    """Return one table definition from the deterministic migration text."""

    match = re.search(
        rf"create table if not exists {re.escape(table_name)}\s*\((.*?)\n\);",
        migration,
        re.IGNORECASE | re.DOTALL,
    )
    assert match is not None, table_name
    return match.group(1)


@pytest.fixture
def registry_db():
    """Yield a throwaway database migrated through the registry schema."""

    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    database_name = f"lineageweave_registry_{uuid.uuid4().hex[:12]}"
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


def _insert_account(cursor, label: str = "operator") -> str:
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


def _insert_snapshot(
    cursor,
    *,
    digest: str = "a" * 64,
    maximum_available_time: str = "2026-08-15T00:00:00Z",
    captured_at: str = "2026-08-15T00:05:00Z",
) -> str:
    """Insert one immutable source snapshot and return its UUID."""

    cursor.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, 'source-contract-v1', %s, %s)
        returning analysis_source_snapshot_id
        """,
        (digest, maximum_available_time, captured_at),
    )
    return str(cursor.fetchone()[0])


def _insert_run(
    cursor,
    *,
    snapshot_id: str,
    account_id: str,
    idempotency_key: str,
    knowledge_cutoff: str = "2026-08-15T00:30:00Z",
    run_kind_code: str = "analysis_run_lineage",
) -> str:
    """Insert one immutable account-scoped analysis request."""

    cursor.execute(
        """
        insert into analysis_run
            (analysis_source_snapshot_id, run_kind_code, idempotency_key,
             requested_by_account_id, knowledge_cutoff,
             configuration_schema_version, configuration_sha256,
             code_revision_sha)
        values (%s, %s, %s, %s, %s, 'lineage-run-v1', %s, %s)
        returning analysis_run_id
        """,
        (
            snapshot_id,
            run_kind_code,
            idempotency_key,
            account_id,
            knowledge_cutoff,
            "b" * 64,
            "c" * 40,
        ),
    )
    return str(cursor.fetchone()[0])


def test_registry_contract_is_normalized_and_has_one_temporal_authority() -> None:
    """Static contract rejects the parallel prototype and duplicated clocks."""

    migration = _REGISTRY_MIGRATION.read_text(encoding="utf-8")
    rollback = _REGISTRY_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    created_tables = set(
        re.findall(r"create table if not exists\s+([a-z0-9_]+)", migration, re.I)
    )
    assert _REQUIRED_TABLES <= created_tables
    assert "analysis_run_records" not in created_tables
    assert "metadata_payload" not in migration
    assert "jsonb" not in migration.casefold()
    assert _REQUIRED_LOOKUP_CODES <= set(
        re.findall(r"'(analysis_[a-z0-9_]+)'", migration)
    )
    assert "0018_analysis_run_registry.sql" in dockerfile
    assert "analysis_run_registry_not_empty" in rollback

    snapshot_definition = _table_definition(migration, "analysis_source_snapshot")
    run_definition = _table_definition(migration, "analysis_run")
    assert "maximum_available_time" in snapshot_definition
    assert "knowledge_cutoff" not in snapshot_definition
    assert "knowledge_cutoff" in run_definition
    assert "requested_by_account_id uuid not null" in run_definition
    assert "unique (requested_by_account_id, idempotency_key)" in run_definition
    assert "enforce_analysis_run_knowledge_cutoff" in migration
    assert "reject_analysis_source_snapshot_update" in migration
    assert "reject_analysis_run_update" in migration
    assert "enforce_analysis_source_count_freeze" in migration
    assert "enforce_analysis_run_status_transition" in migration
    assert "analysis_run_current_status" in migration

    object_patterns = (
        r"create table if not exists\s+([a-z0-9_]+)",
        r"create(?: unique)? index if not exists\s+([a-z0-9_]+)",
        r"create or replace function\s+([a-z0-9_]+)",
        r"create trigger\s+([a-z0-9_]+)",
        r"create or replace view\s+([a-z0-9_]+)",
    )
    for pattern in object_patterns:
        for object_name in re.findall(pattern, migration, re.I):
            assert len(object_name.split("_")) >= 2, object_name


def test_registry_migration_is_idempotent(registry_db) -> None:
    """Sequential migration replay preserves one object set."""

    with registry_db.cursor() as cursor:
        cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "select table_name from information_schema.views "
            "where table_schema = 'public'"
        )
        views = {row[0] for row in cursor.fetchall()}
    assert _REQUIRED_TABLES <= tables
    assert "analysis_run_current_status" in views


def test_registry_persists_scope_counts_and_legal_status_history(registry_db) -> None:
    """A valid run keeps normalized scope, counts, and current status."""

    with registry_db.cursor() as cursor:
        account_id = _insert_account(cursor)
        snapshot_id = _insert_snapshot(cursor)
        cursor.execute(
            "insert into analysis_source_count values "
            "(%s, 'analysis_count_document', 12)",
            (snapshot_id,),
        )
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="synthetic-run-1",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values
                (%s, 1, 'analysis_status_pending', '2026-08-15T01:00:01Z'),
                (%s, 2, 'analysis_status_running', '2026-08-15T01:00:02Z'),
                (%s, 3, 'analysis_status_succeeded', '2026-08-15T01:00:03Z')
            """,
            (run_id, run_id, run_id),
        )
        cursor.execute(
            "select status_code, status_ordinal from analysis_run_current_status "
            "where analysis_run_id = %s",
            (run_id,),
        )
        assert cursor.fetchone() == ("analysis_status_succeeded", 3)


def test_snapshot_supports_multiple_run_owned_cutoffs_and_blocks_future_evidence(
    registry_db,
) -> None:
    """One capture is reusable, but each run must respect its own cutoff."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        first_account_id = _insert_account(cursor, "first")
        second_account_id = _insert_account(cursor, "second")
        first_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=first_account_id,
            idempotency_key="cutoff-one",
            knowledge_cutoff="2026-08-15T00:30:00Z",
        )
        second_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=second_account_id,
            idempotency_key="cutoff-two",
            knowledge_cutoff="2026-08-16T00:00:00Z",
        )
        assert first_run_id != second_run_id
        with pytest.raises(psycopg2.errors.RaiseException):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=first_account_id,
                idempotency_key="future-leakage",
                knowledge_cutoff="2026-08-14T23:59:59Z",
            )


def test_snapshot_counts_and_run_request_are_immutable(registry_db) -> None:
    """Evidence and request configuration freeze before derivation starts."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        cursor.execute(
            "insert into analysis_source_count values "
            "(%s, 'analysis_count_document', 12)",
            (snapshot_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_source_snapshot set source_contract_version = 'x' "
                "where analysis_source_snapshot_id = %s",
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_source_count set count_value = 13 "
                "where analysis_source_snapshot_id = %s",
                (snapshot_id,),
            )
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="freeze-evidence",
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_run set knowledge_cutoff = now() "
                "where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_source_count values "
                "(%s, 'analysis_count_thread', 8)",
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_source_count "
                "where analysis_source_snapshot_id = %s",
                (snapshot_id,),
            )


def test_idempotency_is_scoped_to_the_authenticated_account(registry_db) -> None:
    """Two actors may use one opaque key; one actor may not reuse it."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        first_account_id = _insert_account(cursor, "first")
        second_account_id = _insert_account(cursor, "second")
        _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=first_account_id,
            idempotency_key="shared-key",
        )
        _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=second_account_id,
            idempotency_key="shared-key",
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=first_account_id,
                idempotency_key="shared-key",
            )


def test_registry_rejects_invalid_evidence_and_missing_actor(registry_db) -> None:
    """Database constraints reject malformed audit evidence before persistence."""

    with registry_db.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_source_snapshot "
                "(snapshot_sha256, source_contract_version, "
                "maximum_available_time, captured_at) "
                "values ('bad', 'source-contract-v1', now(), now())"
            )
        snapshot_id = _insert_snapshot(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_source_count values "
                "(%s, 'analysis_count_source_row', -1)",
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cursor.execute(
                """
                insert into analysis_run
                    (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                     knowledge_cutoff, configuration_schema_version,
                     configuration_sha256, code_revision_sha)
                values (%s, 'analysis_run_report', 'missing-actor', now(),
                        'report-run-v1', %s, %s)
                """,
                (snapshot_id, "d" * 64, "e" * 40),
            )


def test_status_history_enforces_shape_order_time_and_legal_transitions(
    registry_db,
) -> None:
    """Append-only status evidence is a serialized state machine."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        first_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="first-status",
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 1, 'analysis_status_running', now())",
                (first_run_id,),
            )

        second_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="second-status",
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z')",
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 3, 'analysis_status_running', "
                "'2026-08-15T01:00:01Z')",
                (second_run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 2, 'analysis_status_succeeded', "
                "'2026-08-15T01:00:01Z')",
                (second_run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 2, 'analysis_status_running', "
            "'2026-08-15T01:00:02Z')",
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 3, 'analysis_status_succeeded', "
                "'2026-08-15T01:00:01Z')",
                (second_run_id,),
            )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 3, 'analysis_status_failed', "
                "'2026-08-15T01:00:03Z')",
                (second_run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 3, 'analysis_status_succeeded', "
            "'2026-08-15T01:00:03Z')",
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 4, 'analysis_status_running', "
                "'2026-08-15T01:00:04Z')",
                (second_run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_run_status_event set retryable = true "
                "where analysis_run_id = %s and status_ordinal = 3",
                (second_run_id,),
            )


def test_rollback_refuses_data_loss_then_removes_an_empty_registry(registry_db) -> None:
    """Downgrade fails closed until audit evidence is explicitly removed."""

    rollback_sql = _REGISTRY_ROLLBACK.read_text(encoding="utf-8")
    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(rollback_sql)
    registry_db.rollback()
    with registry_db.cursor() as cursor:
        cursor.execute(
            "delete from analysis_source_snapshot "
            "where analysis_source_snapshot_id = %s",
            (snapshot_id,),
        )
        cursor.execute(rollback_sql)
        cursor.execute("select to_regclass('public.analysis_run')")
        assert cursor.fetchone()[0] is None
        cursor.execute(rollback_sql)

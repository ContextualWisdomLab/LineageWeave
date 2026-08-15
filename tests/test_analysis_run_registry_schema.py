"""Contracts for the normalized Milestone 2 analysis-run registry."""

from __future__ import annotations

import os
import re
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
_REGISTRY_ROLLBACK = _ROOT / "migrations" / "rollback" / "0018_analysis_run_registry.sql"
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"
_REPAIR_WORKFLOW = (
    _ROOT / ".github" / "workflows" / "pr83-analysis-run-registry-repair.yml"
)
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
    """Replace only the database path while preserving DSN query options."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _table_definition(migration: str, table_name: str) -> str:
    """Return one table definition from the deterministic migration text."""

    match = re.search(
        rf"create table if not exists {re.escape(table_name)}\s*\((.*?)\n\);",
        migration,
        re.I | re.S,
    )
    assert match is not None, table_name
    return match.group(1)


@pytest.fixture
def registry_db():
    """Yield a throwaway database migrated through the analysis registry."""

    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    assert psycopg2 is not None
    assert sql is not None
    database_name = f"lineageweave_analysis_{uuid.uuid4().hex[:12]}"
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
    """Insert one synthetic real-account identity and return its UUID."""

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
    captured_at: str = "2026-08-15T01:00:00Z",
) -> str:
    """Insert one synthetic immutable snapshot and return its identifier."""

    cursor.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, %s, %s, %s)
        returning analysis_source_snapshot_id
        """,
        (digest, "source-contract-v1", maximum_available_time, captured_at),
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
    """Insert one synthetic account-scoped analysis request."""

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


def test_registry_contract_files_are_present_and_normalized() -> None:
    """The additive bridge fixes temporal facts at their functional owners."""

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
    assert "analysis_run_current_status" in migration
    assert _REQUIRED_LOOKUP_CODES <= set(
        re.findall(r"'(analysis_[a-z0-9_]+)'", migration)
    )
    assert "0018_analysis_run_registry.sql" in dockerfile
    assert "analysis_run_registry_not_empty" in rollback
    assert not _REPAIR_WORKFLOW.exists()

    snapshot_definition = _table_definition(migration, "analysis_source_snapshot")
    run_definition = _table_definition(migration, "analysis_run")
    assert "maximum_available_time" in snapshot_definition
    assert "knowledge_cutoff" not in snapshot_definition
    assert "knowledge_cutoff" in run_definition
    assert "requested_by_account_id uuid not null" in run_definition
    assert "unique (requested_by_account_id, idempotency_key)" in run_definition
    assert "enforce_analysis_run_knowledge_cutoff" in migration
    assert "enforce_analysis_run_status_transition" in migration
    assert "reject_analysis_source_snapshot_update" in migration
    assert "enforce_analysis_source_count_freeze" in migration
    for table_name in created_tables:
        assert len(table_name.split("_")) >= 2


def test_registry_migration_is_idempotent(registry_db) -> None:
    """The sequential migration can be replayed without duplicating objects."""

    with registry_db.cursor() as cursor:
        cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
        cursor.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
            """
        )
        tables = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            select table_name
            from information_schema.views
            where table_schema = 'public'
            """
        )
        views = {row[0] for row in cursor.fetchall()}
    assert _REQUIRED_TABLES <= tables
    assert "analysis_run_current_status" in views


def test_registry_persists_normalized_snapshot_scope_and_status(registry_db) -> None:
    """A run references one snapshot, one scope, and a legal status history."""

    with registry_db.cursor() as cursor:
        account_id = _insert_account(cursor)
        snapshot_id = _insert_snapshot(cursor)
        cursor.execute(
            """
            insert into analysis_source_count
                (analysis_source_snapshot_id, count_type_code, count_value)
            values (%s, 'analysis_count_document', 12)
            """,
            (snapshot_id,),
        )
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="synthetic-run-1",
        )
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code)
            values (%s, 'analysis_scope_all_visible')
            """,
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
            """
            select status_code, status_ordinal
            from analysis_run_current_status
            where analysis_run_id = %s
            """,
            (run_id,),
        )
        current_status = cursor.fetchone()
        cursor.execute(
            """
            select count_value
            from analysis_source_count
            where analysis_source_snapshot_id = %s
              and count_type_code = 'analysis_count_document'
            """,
            (snapshot_id,),
        )
        count_value = cursor.fetchone()[0]
    assert current_status == ("analysis_status_succeeded", 3)
    assert count_value == 12


def test_snapshot_is_reusable_across_run_owned_knowledge_cutoffs(registry_db) -> None:
    """One immutable capture can support multiple later analysis cutoffs."""

    assert psycopg2 is not None
    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(
            cursor,
            maximum_available_time="2026-08-15T00:00:00Z",
            captured_at="2026-08-15T00:05:00Z",
        )
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


def test_snapshot_and_counts_are_immutable_and_freeze_at_first_run(registry_db) -> None:
    """A run cannot derive from evidence that can still be rewritten."""

    assert psycopg2 is not None
    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        cursor.execute(
            """
            insert into analysis_source_count
                (analysis_source_snapshot_id, count_type_code, count_value)
            values (%s, 'analysis_count_document', 12)
            """,
            (snapshot_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                update analysis_source_snapshot
                   set source_contract_version = 'rewritten'
                 where analysis_source_snapshot_id = %s
                """,
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                update analysis_source_count
                   set count_value = 13
                 where analysis_source_snapshot_id = %s
                """,
                (snapshot_id,),
            )
        account_id = _insert_account(cursor)
        _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="freeze-evidence",
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                insert into analysis_source_count
                    (analysis_source_snapshot_id, count_type_code, count_value)
                values (%s, 'analysis_count_thread', 8)
                """,
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                delete from analysis_source_count
                 where analysis_source_snapshot_id = %s
                   and count_type_code = 'analysis_count_document'
                """,
                (snapshot_id,),
            )


def test_idempotency_keys_are_scoped_to_the_requesting_account(registry_db) -> None:
    """Independent authenticated actors may choose the same opaque key."""

    assert psycopg2 is not None
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


def test_registry_rejects_invalid_hashes_negative_counts_and_missing_actor(registry_db) -> None:
    """Integrity constraints fail closed before untrusted audit data persists."""

    assert psycopg2 is not None
    with registry_db.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                insert into analysis_source_snapshot
                    (snapshot_sha256, source_contract_version,
                     maximum_available_time, captured_at)
                values ('not-a-digest', 'source-contract-v1', now(), now())
                """
            )
        snapshot_id = _insert_snapshot(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                insert into analysis_source_count
                    (analysis_source_snapshot_id, count_type_code, count_value)
                values (%s, 'analysis_count_source_row', -1)
                """,
                (snapshot_id,),
            )
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cursor.execute(
                """
                insert into analysis_run
                    (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                     knowledge_cutoff, configuration_schema_version,
                     configuration_sha256, code_revision_sha)
                values (%s, 'analysis_run_report', 'missing-actor',
                        '2026-08-15T00:30:00Z', 'report-run-v1', %s, %s)
                """,
                (snapshot_id, "d" * 64, "e" * 40),
            )


def test_registry_rejects_incoherent_scope_and_failure_events(registry_db) -> None:
    """Scope discriminators and failure metadata must agree with their codes."""

    assert psycopg2 is not None
    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scope-check",
            run_kind_code="analysis_run_tepp",
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                insert into analysis_run_scope
                    (analysis_run_id, scope_kind_code, scope_key)
                values (%s, 'analysis_scope_all_visible', 'unexpected')
                """,
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                insert into analysis_run_scope
                    (analysis_run_id, scope_kind_code)
                values (%s, 'analysis_scope_thread_group')
                """,
                (run_id,),
            )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, 1, 'analysis_status_pending', '2026-08-15T01:00:00Z')
            """,
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 2, 'analysis_status_failed', '2026-08-15T01:00:01Z')
                """,
                (run_id,),
            )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at,
                 failure_code, retryable)
            values (%s, 2, 'analysis_status_failed', '2026-08-15T01:00:01Z',
                    'synthetic_failure', true)
            """,
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                update analysis_run_status_event
                   set retryable = false
                 where analysis_run_id = %s and status_ordinal = 2
                """,
                (run_id,),
            )


def test_status_history_enforces_contiguous_monotonic_legal_transitions(registry_db) -> None:
    """Run state is an ordered state machine rather than an arbitrary event bag."""

    assert psycopg2 is not None
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
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 1, 'analysis_status_running', '2026-08-15T01:00:00Z')
                """,
                (first_run_id,),
            )

        second_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="second-status",
        )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, 1, 'analysis_status_pending', '2026-08-15T01:00:00Z')
            """,
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 3, 'analysis_status_running', '2026-08-15T01:00:01Z')
                """,
                (second_run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 2, 'analysis_status_succeeded', '2026-08-15T01:00:01Z')
                """,
                (second_run_id,),
            )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, 2, 'analysis_status_running', '2026-08-15T01:00:02Z')
            """,
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 3, 'analysis_status_succeeded', '2026-08-15T01:00:01Z')
                """,
                (second_run_id,),
            )
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, 3, 'analysis_status_succeeded', '2026-08-15T01:00:03Z')
            """,
            (second_run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, 4, 'analysis_status_running', '2026-08-15T01:00:04Z')
                """,
                (second_run_id,),
            )


def test_rollback_refuses_data_loss_and_succeeds_after_explicit_cleanup(registry_db) -> None:
    """Downgrade is fail-closed while registry evidence still exists."""

    assert psycopg2 is not None
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

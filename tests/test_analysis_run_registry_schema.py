"""Real-PostgreSQL contracts for the normalized Milestone 2 run registry."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lineageweave import postgres_sync as psycopg2
from lineageweave.postgres_sync import sql

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_REGISTRY_ROLLBACK = _ROOT / "migrations" / "rollback" / "0018_analysis_run_registry.sql"
_RETENTION_MIGRATION = _ROOT / "migrations" / "0020_analysis_run_retention_purge.sql"
_RETENTION_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0020_analysis_run_retention_purge.sql"
)
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
    requested_at: str = "2026-08-15T00:45:00Z",
) -> str:
    """Insert one immutable account-scoped analysis request."""

    cursor.execute(
        """
        insert into analysis_run
            (analysis_source_snapshot_id, run_kind_code, idempotency_key,
             requested_by_account_id, knowledge_cutoff,
             configuration_schema_version, configuration_sha256,
             code_revision_sha, requested_at)
        values (%s, %s, %s, %s, %s, 'lineage-run-v1', %s, %s, %s)
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
            requested_at,
        ),
    )
    return str(cursor.fetchone()[0])


def _insert_run_bearing_registry(
    cursor,
    *,
    digest: str,
    idempotency_key: str,
) -> None:
    """Insert one snapshot, count, run, scope, and pending event."""

    account_id = _insert_account(cursor)
    snapshot_id = _insert_snapshot(cursor, digest=digest)
    cursor.execute(
        "insert into analysis_source_count values "
        "(%s, 'analysis_count_document', 3)",
        (snapshot_id,),
    )
    run_id = _insert_run(
        cursor,
        snapshot_id=snapshot_id,
        account_id=account_id,
        idempotency_key=idempotency_key,
    )
    cursor.execute(
        "insert into analysis_run_scope "
        "(analysis_run_id, scope_kind_code) "
        "values (%s, 'analysis_scope_all_visible')",
        (run_id,),
    )
    cursor.execute(
        "insert into analysis_run_status_event "
        "(analysis_run_id, status_ordinal, status_code, occurred_at) "
        "values (%s, 1, 'analysis_status_pending', "
        "'2026-08-15T01:00:00Z')",
        (run_id,),
    )


def _authorize_session_for_purge(cursor) -> str:
    """Grant the current session_user both retention locks and return it."""

    cursor.execute("select session_user")
    session_role = cursor.fetchone()[0]
    cursor.execute(
        "insert into analysis_run_retention_grant (database_role_name) "
        "select %s "
        "where not exists ("
        "    select 1 from analysis_run_retention_grant "
        "    where database_role_name = %s and revoked_at is null"
        ")",
        (session_role, session_role),
    )
    cursor.execute(
        sql.SQL("grant analysis_run_retention_admin to {}").format(
            sql.Identifier(session_role)
        )
    )
    return session_role


def _drop_role_if_exists(cursor, role_name: str) -> None:
    """Drop a test role after releasing objects it owns."""

    cursor.execute("select 1 from pg_roles where rolname = %s", (role_name,))
    if cursor.fetchone() is None:
        return
    cursor.execute(sql.SQL("drop owned by {}").format(sql.Identifier(role_name)))
    cursor.execute(sql.SQL("drop role {}").format(sql.Identifier(role_name)))


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
    assert "0019_role_catalog_identity.sql" in dockerfile
    assert "0020_analysis_run_retention_purge.sql" in dockerfile
    assert "0021_analysis_run_reconstruction.sql" in dockerfile
    assert "0022_analysis_source_snapshot_member.sql" in dockerfile
    assert "0023_analysis_run_outbox.sql" in dockerfile
    assert "0024_source_post_revision.sql" in dockerfile
    assert "0025_role_person_catalog_identity.sql" in dockerfile
    seed = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    assert seed.index("0019_role_catalog_identity.sql") < seed.index(
        "0020_analysis_run_retention_purge.sql"
    )
    assert seed.index("0020_analysis_run_retention_purge.sql") < seed.index(
        "0021_analysis_run_reconstruction.sql"
    )
    assert seed.index("0021_analysis_run_reconstruction.sql") < seed.index(
        "0022_analysis_source_snapshot_member.sql"
    )
    assert seed.index("0022_analysis_source_snapshot_member.sql") < seed.index(
        "0023_analysis_run_outbox.sql"
    )
    assert seed.index("0023_analysis_run_outbox.sql") < seed.index(
        "0024_source_post_revision.sql"
    )
    assert seed.index("0024_source_post_revision.sql") < seed.index(
        "0025_role_person_catalog_identity.sql"
    )
    assert "analysis_run_registry_not_empty" in rollback
    retention = _RETENTION_MIGRATION.read_text(encoding="utf-8")
    retention_rollback = _RETENTION_ROLLBACK.read_text(encoding="utf-8")
    assert "purge_analysis_run_registry" in retention
    assert "analysis_run_retention_event" in retention
    assert "analysis_run_retention_grant" in retention
    assert "analysis_run_retention_admin" in retention
    assert "invoking_session_role" in retention
    assert "invoking_current_role" in retention
    assert "security definer" in retention.casefold()
    assert "revoke all" in retention.casefold()
    assert "from public" in retention.casefold()
    assert "analysis_run_retention_not_approved" in retention
    assert "analysis_run_retention_not_granted" in retention
    assert "analysis_run_retention_not_admin" in retention
    assert "analysis_run_retention_event_not_empty" in retention_rollback
    assert "jsonb" not in retention.casefold()
    for object_name in re.findall(
        r"create table if not exists\s+([a-z0-9_]+)"
        r"|create or replace function\s+([a-z0-9_]+)"
        r"|create role\s+([a-z0-9_]+)",
        retention,
        re.I,
    ):
        name = object_name[0] or object_name[1] or object_name[2]
        assert len(name.split("_")) >= 2, name

    snapshot_definition = _table_definition(migration, "analysis_source_snapshot")
    run_definition = _table_definition(migration, "analysis_run")
    assert "maximum_available_time" in snapshot_definition
    assert "knowledge_cutoff" not in snapshot_definition
    assert "knowledge_cutoff" in run_definition
    assert "requested_by_account_id uuid not null" in run_definition
    assert "unique (requested_by_account_id, idempotency_key)" in run_definition
    assert "enforce_analysis_run_knowledge_cutoff" in migration
    assert "reject_analysis_source_snapshot_update" in migration
    assert "reject_analysis_run_mutation" in migration
    assert "reject_analysis_run_scope_mutation" in migration
    assert "analysis_run_scope_required" in migration
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
        cursor.execute(_RETENTION_MIGRATION.read_text(encoding="utf-8"))
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
    assert "analysis_run_retention_event" in tables
    assert "analysis_run_retention_grant" in tables
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
            requested_at="2026-08-16T00:30:00Z",
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
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (first_run_id,),
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
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (second_run_id,),
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



def test_run_scope_and_request_evidence_are_immutable(registry_db) -> None:
    """Authorization scope and request identity cannot be rewritten or erased."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="immutable-run",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_run_scope set scope_kind_code = scope_kind_code "
                "where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run_scope where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run where analysis_run_id = %s",
                (run_id,),
            )


def test_status_requires_scope_and_cannot_predate_request(registry_db) -> None:
    """Lifecycle evidence starts only after an immutable authorized request."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scoped-status",
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 1, 'analysis_status_pending', "
                "'2026-08-15T01:00:00Z')",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 1, 'analysis_status_pending', "
                "'2026-08-15T00:44:59Z')",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at, recorded_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z', '2099-01-01T00:00:00Z') "
            "returning recorded_at",
            (run_id,),
        )
        recorded_at = cursor.fetchone()[0]
    assert recorded_at.year < 2099


def test_machine_codes_and_canonical_idempotency_are_fail_closed(registry_db) -> None:
    """Audit identifiers are canonical and failure details stay machine-safe."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key="future-request",
                requested_at="2099-01-01T00:00:00Z",
            )
        with pytest.raises(psycopg2.errors.CheckViolation):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key=" padded-key ",
            )
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="machine-safe",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z')",
            (run_id,),
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 2, 'analysis_status_running', "
            "'2026-08-15T01:00:00Z')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at, "
                "failure_code, retryable) "
                "values (%s, 3, 'analysis_status_failed', "
                "'2026-08-15T01:00:00Z', 'provider timeout', true)",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at, "
            "failure_code, retryable) "
            "values (%s, 3, 'analysis_status_failed', "
            "'2026-08-15T01:00:00Z', 'provider_timeout', true)",
            (run_id,),
        )

def test_rollback_refuses_data_loss_then_removes_an_empty_registry(registry_db) -> None:
    """Downgrade fails closed until audit evidence is explicitly removed."""

    rollback_sql = _REGISTRY_ROLLBACK.read_text(encoding="utf-8")
    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(rollback_sql)
        # The rollback script opens an explicit transaction on this
        # autocommit connection. A RAISE leaves that transaction aborted, and
        # connection.rollback() is a no-op while autocommit is true.
        cursor.execute("rollback")
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


def test_approved_retention_purge_empties_a_run_bearing_registry(registry_db) -> None:
    """Grant plus admin empties expired registry rows; a raw DELETE still fails."""

    rollback_sql = _REGISTRY_ROLLBACK.read_text(encoding="utf-8")
    retention_rollback = _RETENTION_ROLLBACK.read_text(encoding="utf-8")
    with registry_db.cursor() as cursor:
        _insert_run_bearing_registry(
            cursor,
            digest="a" * 64,
            idempotency_key="retention-purge",
        )
        cursor.execute("select analysis_run_id from analysis_run")
        run_id = cursor.fetchone()[0]
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_request_is_immutable",
        ):
            cursor.execute(
                "delete from analysis_run where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_registry_not_empty",
        ):
            cursor.execute(rollback_sql)
        cursor.execute("rollback")
        session_role = _authorize_session_for_purge(cursor)
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_retention_not_approved",
        ):
            cursor.execute("select purge_analysis_run_registry(%s)", ("wrong-token",))
        cursor.execute(
            "select purge_analysis_run_registry(%s)",
            ("approved-retention-purge",),
        )
        cursor.execute("select count(*) from analysis_run")
        assert cursor.fetchone()[0] == 0
        cursor.execute("select count(*) from analysis_source_snapshot")
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "select purged_run_count, purged_snapshot_count, "
            "approval_token_digest, invoking_session_role, "
            "invoking_current_role from analysis_run_retention_event"
        )
        (
            purged_run_count,
            purged_snapshot_count,
            token_digest,
            invoking_session_role,
            invoking_current_role,
        ) = cursor.fetchone()
        assert purged_run_count == 1
        assert purged_snapshot_count == 1
        assert token_digest == hashlib.sha256(
            b"approved-retention-purge"
        ).hexdigest()
        assert invoking_session_role == session_role
        assert invoking_current_role
        cursor.execute(rollback_sql)
        cursor.execute("select to_regclass('public.analysis_run')")
        assert cursor.fetchone()[0] is None
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_retention_event_not_empty",
        ):
            cursor.execute(retention_rollback)
        cursor.execute("rollback")
        cursor.execute("delete from analysis_run_retention_event")
        cursor.execute(retention_rollback)
        cursor.execute(
            "select to_regclass('public.analysis_run_retention_event')"
        )
        assert cursor.fetchone()[0] is None


def test_retention_purge_requires_unrevoked_session_grant(registry_db) -> None:
    """Admin membership plus the published token cannot purge without a grant."""

    role_name = f"retention_denied_{uuid.uuid4().hex[:8]}"
    with registry_db.cursor() as cursor:
        cursor.execute(
            "select has_function_privilege(%s, %s, 'execute')",
            ("public", "purge_analysis_run_registry(text)"),
        )
        assert cursor.fetchone()[0] is False
        _insert_run_bearing_registry(
            cursor,
            digest="d" * 64,
            idempotency_key="retention-grant-deny",
        )
        cursor.execute(
            sql.SQL("create role {} nologin nosuperuser inherit").format(
                sql.Identifier(role_name)
            )
        )
        cursor.execute(
            sql.SQL("grant analysis_run_retention_admin to {}").format(
                sql.Identifier(role_name)
            )
        )
        try:
            cursor.execute(
                sql.SQL("set session authorization {}").format(
                    sql.Identifier(role_name)
                )
            )
        except psycopg2.errors.InsufficientPrivilege:
            cursor.execute("reset session authorization")
            _drop_role_if_exists(cursor, role_name)
            pytest.skip("session authorization requires superuser")
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_retention_not_granted",
        ):
            cursor.execute(
                "select purge_analysis_run_registry(%s)",
                ("approved-retention-purge",),
            )
        cursor.execute("reset session authorization")
        cursor.execute(
            "insert into analysis_run_retention_grant (database_role_name) "
            "values (%s)",
            (role_name,),
        )
        cursor.execute(
            sql.SQL("set session authorization {}").format(
                sql.Identifier(role_name)
            )
        )
        cursor.execute(
            "select purge_analysis_run_registry(%s)",
            ("approved-retention-purge",),
        )
        cursor.execute("reset session authorization")
        cursor.execute(
            "select invoking_session_role from analysis_run_retention_event"
        )
        assert cursor.fetchone()[0] == role_name
        cursor.execute(
            "update analysis_run_retention_grant "
            "set revoked_at = clock_timestamp() "
            "where database_role_name = %s and revoked_at is null",
            (role_name,),
        )
        _insert_run_bearing_registry(
            cursor,
            digest="e" * 64,
            idempotency_key="retention-grant-revoked",
        )
        cursor.execute(
            sql.SQL("set session authorization {}").format(
                sql.Identifier(role_name)
            )
        )
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_retention_not_granted",
        ):
            cursor.execute(
                "select purge_analysis_run_registry(%s)",
                ("approved-retention-purge",),
            )
        cursor.execute("reset session authorization")
        _drop_role_if_exists(cursor, role_name)


def test_runtime_role_cannot_purge_with_only_the_public_token(registry_db) -> None:
    """Table DML plus the documented phrase is not a retention grant."""

    runtime_role = f"analysis_run_app_{uuid.uuid4().hex[:12]}"
    operator_role = f"analysis_run_operator_{uuid.uuid4().hex[:12]}"
    try:
        with registry_db.cursor() as cursor:
            _insert_run_bearing_registry(
                cursor,
                digest="f" * 64,
                idempotency_key="runtime-denied-purge",
            )
            cursor.execute("select analysis_run_id from analysis_run")
            run_id = cursor.fetchone()[0]
            cursor.execute(
                sql.SQL(
                    "create role {} nologin nosuperuser inherit"
                ).format(sql.Identifier(runtime_role))
            )
            cursor.execute(
                sql.SQL(
                    "create role {} nologin nosuperuser inherit"
                ).format(sql.Identifier(operator_role))
            )
            cursor.execute(
                sql.SQL("grant usage on schema public to {}, {}").format(
                    sql.Identifier(runtime_role),
                    sql.Identifier(operator_role),
                )
            )
            cursor.execute(
                sql.SQL(
                    "grant select, insert, update, delete on "
                    "analysis_run, analysis_run_scope, "
                    "analysis_run_status_event, analysis_source_snapshot, "
                    "analysis_source_count to {}"
                ).format(sql.Identifier(runtime_role))
            )
            cursor.execute(
                sql.SQL("grant analysis_run_retention_admin to {}").format(
                    sql.Identifier(operator_role)
                )
            )
            cursor.execute(
                "insert into analysis_run_retention_grant (database_role_name) "
                "values (%s)",
                (operator_role,),
            )
            cursor.execute(
                sql.SQL("set role {}").format(sql.Identifier(runtime_role))
            )
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cursor.execute(
                    "select purge_analysis_run_registry(%s)",
                    ("approved-retention-purge",),
                )
            with pytest.raises(
                psycopg2.errors.RaiseException,
                match="analysis_run_request_is_immutable",
            ):
                cursor.execute(
                    "delete from analysis_run where analysis_run_id = %s",
                    (run_id,),
                )
            cursor.execute("reset role")
            try:
                cursor.execute(
                    sql.SQL("set session authorization {}").format(
                        sql.Identifier(operator_role)
                    )
                )
            except psycopg2.errors.InsufficientPrivilege:
                cursor.execute("reset session authorization")
                pytest.skip("session authorization requires superuser")
            cursor.execute(
                "select purge_analysis_run_registry(%s)",
                ("approved-retention-purge",),
            )
            cursor.execute("reset session authorization")
            cursor.execute("select count(*) from analysis_run")
            assert cursor.fetchone()[0] == 0
            cursor.execute(
                "select invoking_session_role, invoking_current_role "
                "from analysis_run_retention_event"
            )
            invoking_session_role, invoking_current_role = cursor.fetchone()
            assert invoking_session_role
            assert invoking_current_role
    finally:
        with registry_db.cursor() as cursor:
            cursor.execute("reset role")
            cursor.execute("reset session authorization")
            for role_name in (runtime_role, operator_role):
                _drop_role_if_exists(cursor, role_name)


def test_retention_purge_requires_admin_membership_even_with_a_grant(
    registry_db,
) -> None:
    """A grant without analysis_run_retention_admin cannot empty the registry."""

    role_name = f"retention_grant_only_{uuid.uuid4().hex[:8]}"
    with registry_db.cursor() as cursor:
        _insert_run_bearing_registry(
            cursor,
            digest="c" * 64,
            idempotency_key="retention-admin-deny",
        )
        cursor.execute(
            sql.SQL("create role {} nologin nosuperuser inherit").format(
                sql.Identifier(role_name)
            )
        )
        cursor.execute(
            sql.SQL(
                "grant execute on function purge_analysis_run_registry(text) "
                "to {}"
            ).format(sql.Identifier(role_name))
        )
        cursor.execute(
            "insert into analysis_run_retention_grant (database_role_name) "
            "values (%s)",
            (role_name,),
        )
        try:
            cursor.execute(
                sql.SQL("set session authorization {}").format(
                    sql.Identifier(role_name)
                )
            )
        except psycopg2.errors.InsufficientPrivilege:
            cursor.execute("reset session authorization")
            _drop_role_if_exists(cursor, role_name)
            pytest.skip("session authorization requires superuser")
        with pytest.raises(
            psycopg2.errors.RaiseException,
            match="analysis_run_retention_not_admin",
        ):
            cursor.execute(
                "select purge_analysis_run_registry(%s)",
                ("approved-retention-purge",),
            )
        cursor.execute("reset session authorization")
        cursor.execute("select count(*) from analysis_run")
        assert cursor.fetchone()[0] == 1
        _drop_role_if_exists(cursor, role_name)

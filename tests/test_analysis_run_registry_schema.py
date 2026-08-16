"""Real-PostgreSQL contracts for the Milestone 2.1 analysis-run registry.

TDD split:

- After migrations ``0001``–``0011`` the registry objects must be absent.
- After ``0012_analysis_run_registry.sql`` they must exist and enforce the
  temporal, immutability, idempotency, orphan, and lifecycle contracts.

Skipped unless a local PostgreSQL server is reachable
(``LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN``).
"""

from __future__ import annotations

import os
import re
import threading
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest
from psycopg2 import sql

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _ROOT / "migrations"
_REGISTRY_MIGRATION = _MIGRATIONS_DIR / "0012_analysis_run_registry.sql"
_REGISTRY_ROLLBACK = _MIGRATIONS_DIR / "rollback" / "0012_analysis_run_registry.sql"
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


def _forward_migrations() -> list[Path]:
    """Return ``0001``–``0012`` (and any later peers) in lexical order."""

    return sorted(
        path
        for path in _MIGRATIONS_DIR.glob("*.sql")
        if path.name[0:4].isdigit()
    )


def _migrations_through(last_name: str) -> list[Path]:
    """Return forward migrations up to and including ``last_name``."""

    selected: list[Path] = []
    for path in _forward_migrations():
        selected.append(path)
        if path.name == last_name:
            return selected
    raise AssertionError(f"migration {last_name} is not in migrations/")


def _apply_sql_files(connection, paths: list[Path]) -> None:
    """Execute each migration file against ``connection``."""

    with connection.cursor() as cursor:
        for path in paths:
            cursor.execute(path.read_text(encoding="utf-8"))


def _public_tables(cursor) -> set[str]:
    """Return public base-table names."""

    cursor.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' and table_type = 'BASE TABLE'"
    )
    return {row[0] for row in cursor.fetchall()}


def _public_views(cursor) -> set[str]:
    """Return public view names."""

    cursor.execute(
        "select table_name from information_schema.views "
        "where table_schema = 'public'"
    )
    return {row[0] for row in cursor.fetchall()}


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
def ephemeral_db():
    """Yield ``(connection, dsn)`` for a throwaway database, then drop it."""

    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    database_name = f"lineageweave_registry_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(database_name))
        )
    dsn = _database_dsn(database_name)
    try:
        connection = psycopg2.connect(dsn)
        try:
            connection.autocommit = True
            yield connection, dsn
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
        admin_connection.close()


@pytest.fixture
def schema_through_0011(ephemeral_db):
    """Throwaway database migrated through the protected ``0001``–``0011`` chain."""

    connection, dsn = ephemeral_db
    _apply_sql_files(connection, _migrations_through("0011_post_chat_result.sql"))
    return connection, dsn


@pytest.fixture
def registry_db(ephemeral_db):
    """Throwaway database migrated through the registry schema."""

    connection, dsn = ephemeral_db
    _apply_sql_files(connection, _migrations_through("0012_analysis_run_registry.sql"))
    return connection, dsn


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
    digest: str | None = None,
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
            (digest or uuid.uuid4().hex + uuid.uuid4().hex, maximum_available_time, captured_at),
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


def _insert_all_visible_scope(cursor, run_id: str) -> None:
    """Attach the all-visible authorization scope to ``run_id``."""

    cursor.execute(
        "insert into analysis_run_scope "
        "(analysis_run_id, scope_kind_code) "
        "values (%s, 'analysis_scope_all_visible')",
        (run_id,),
    )


def test_registry_objects_are_absent_after_0011_upgrade(schema_through_0011) -> None:
    """Protected main's 0001–0011 chain has no analysis-run registry yet."""

    connection, _dsn = schema_through_0011
    with connection.cursor() as cursor:
        tables = _public_tables(cursor)
        views = _public_views(cursor)
    assert _REQUIRED_TABLES.isdisjoint(tables)
    assert "analysis_run_current_status" not in views
    assert "analysis_run_current_status" not in tables


def test_registry_contract_is_normalized_and_has_one_temporal_authority() -> None:
    """Static contract rejects a second mutable status table and duplicated clocks."""

    assert _REGISTRY_MIGRATION.is_file(), "0012_analysis_run_registry.sql must exist"
    assert _REGISTRY_ROLLBACK.is_file(), "rollback/0012_analysis_run_registry.sql must exist"
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
    assert " text[]" not in migration.casefold()
    assert _REQUIRED_LOOKUP_CODES <= set(
        re.findall(r"'(analysis_[a-z0-9_]+)'", migration)
    )
    assert "0012_analysis_run_registry.sql" in dockerfile
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
    assert "reject_analysis_run_mutation" in migration
    assert "reject_analysis_run_scope_mutation" in migration
    assert "analysis_run_scope_required" in migration
    assert "enforce_analysis_source_count_freeze" in migration
    assert "enforce_analysis_run_status_transition" in migration
    assert "create or replace view analysis_run_current_status" in migration.casefold()

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


def test_fresh_install_and_sequential_upgrade_converge(ephemeral_db) -> None:
    """A new database and a 0001–0011 upgrade both reach the same registry."""

    connection, _dsn = ephemeral_db
    _apply_sql_files(connection, _migrations_through("0012_analysis_run_registry.sql"))
    with connection.cursor() as cursor:
        fresh_tables = _public_tables(cursor)
        fresh_views = _public_views(cursor)
        cursor.execute(
            "select lookup_code from common_lookup_value "
            "where lookup_code like 'analysis_%'"
        )
        fresh_codes = {row[0] for row in cursor.fetchall()}

    connection2_name = f"lineageweave_upgrade_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(connection2_name))
        )
    try:
        upgrade = psycopg2.connect(_database_dsn(connection2_name))
        try:
            upgrade.autocommit = True
            _apply_sql_files(upgrade, _migrations_through("0011_post_chat_result.sql"))
            with upgrade.cursor() as cursor:
                assert _REQUIRED_TABLES.isdisjoint(_public_tables(cursor))
            _apply_sql_files(upgrade, [_REGISTRY_MIGRATION])
            with upgrade.cursor() as cursor:
                upgraded_tables = _public_tables(cursor)
                upgraded_views = _public_views(cursor)
                cursor.execute(
                    "select lookup_code from common_lookup_value "
                    "where lookup_code like 'analysis_%'"
                )
                upgraded_codes = {row[0] for row in cursor.fetchall()}
        finally:
            upgrade.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(connection2_name))
            )
        admin_connection.close()

    assert _REQUIRED_TABLES <= fresh_tables
    assert _REQUIRED_TABLES <= upgraded_tables
    assert "analysis_run_current_status" in fresh_views
    assert "analysis_run_current_status" in upgraded_views
    assert _REQUIRED_LOOKUP_CODES <= fresh_codes
    assert fresh_codes == upgraded_codes


def test_registry_migration_is_idempotent(registry_db) -> None:
    """Sequential migration replay preserves one object set."""

    connection, _dsn = registry_db
    _apply_sql_files(connection, [_REGISTRY_MIGRATION])
    with connection.cursor() as cursor:
        tables = _public_tables(cursor)
        views = _public_views(cursor)
    assert _REQUIRED_TABLES <= tables
    assert "analysis_run_current_status" in views


def test_registry_persists_scope_counts_and_legal_status_history(registry_db) -> None:
    """A valid run keeps normalized scope, counts, and current status."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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
        _insert_all_visible_scope(cursor, run_id)
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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


def test_concurrent_account_idempotency_has_one_winner(registry_db) -> None:
    """Two concurrent inserts of the same account key leave exactly one run."""

    connection, dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor, "racer")

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _race() -> None:
        raced = psycopg2.connect(dsn)
        raced.autocommit = True
        try:
            with raced.cursor() as cursor:
                barrier.wait(timeout=5)
                try:
                    _insert_run(
                        cursor,
                        snapshot_id=snapshot_id,
                        account_id=account_id,
                        idempotency_key="concurrent-key",
                    )
                    result = "inserted"
                except psycopg2.errors.UniqueViolation:
                    result = "conflict"
            with lock:
                outcomes.append(result)
        finally:
            raced.close()

    workers = [threading.Thread(target=_race) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)
    assert outcomes.count("inserted") == 1
    assert outcomes.count("conflict") == 1
    with connection.cursor() as cursor:
        cursor.execute(
            "select count(*) from analysis_run "
            "where requested_by_account_id = %s and idempotency_key = %s",
            (account_id, "concurrent-key"),
        )
        assert cursor.fetchone()[0] == 1


def test_registry_rejects_orphans_and_missing_actor(registry_db) -> None:
    """Foreign keys reject dangling evidence; a run requires an actor."""

    connection, _dsn = registry_db
    missing = str(uuid.uuid4())
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cursor.execute(
                "insert into analysis_source_count values "
                "(%s, 'analysis_count_source_row', 1)",
                (missing,),
            )
        with pytest.raises(psycopg2.errors.RaiseException, match="snapshot_not_found"):
            cursor.execute(
                """
                insert into analysis_run
                    (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                     requested_by_account_id, knowledge_cutoff,
                     configuration_schema_version, configuration_sha256,
                     code_revision_sha, requested_at)
                values (%s, 'analysis_run_lineage', 'orphan-run', %s,
                        '2026-08-15T00:30:00Z', 'lineage-run-v1', %s, %s,
                        '2026-08-15T00:45:00Z')
                """,
                (missing, missing, "b" * 64, "c" * 40),
            )
            snapshot_id = _insert_snapshot(cursor)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute(
                    "insert into analysis_source_count values "
                    "(%s, 'analysis_count_source_row', -1)",
                    (snapshot_id,),
                )
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute(
                    "insert into analysis_source_snapshot "
                    "(snapshot_sha256, source_contract_version, "
                    "maximum_available_time, captured_at) "
                    "values ('bad', 'source-contract-v1', now(), now())"
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
            account_id = _insert_account(cursor)
            run_id = _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key="scope-orphan",
            )
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute(
                    "insert into analysis_run_scope "
                    "(analysis_run_id, scope_kind_code, corporate_entity_id) "
                    "values (%s, 'analysis_scope_corporate_entity', %s)",
                    (run_id, missing),
                )


def test_scope_shapes_cover_all_four_vocabularies(registry_db) -> None:
    """Each scope kind accepts only its declared foreign-key shape."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into common_lookup_value "
            "(lookup_category, lookup_code, lookup_label) values "
            "('corporate_entity_level', 'group', 'Group')"
        )
        cursor.execute(
            "insert into corporate_entity "
            "(corporate_entity_code, entity_name, entity_level_code) "
            "values ('DEMO-CORP', 'Demo Corp', 'group') "
            "returning corporate_entity_id"
        )
        entity_id = str(cursor.fetchone()[0])
        cursor.execute(
            "insert into process_unit "
            "(corporate_entity_id, process_unit_code, process_unit_name) "
            "values (%s, 'DEMO-PU', 'Demo process unit') "
            "returning process_unit_id",
            (entity_id,),
        )
        process_unit_id = str(cursor.fetchone()[0])
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)

        entity_run = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scope-entity",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code, corporate_entity_id) "
            "values (%s, 'analysis_scope_corporate_entity', %s)",
            (entity_run, entity_id),
        )
        unit_run = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scope-unit",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code, process_unit_id) "
            "values (%s, 'analysis_scope_process_unit', %s)",
            (unit_run, process_unit_id),
        )
        thread_run = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scope-thread",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code, scope_key) "
            "values (%s, 'analysis_scope_thread_group', 'A-100')",
            (thread_run,),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            visible_run = _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key="scope-bad-visible",
            )
            cursor.execute(
                "insert into analysis_run_scope "
                "(analysis_run_id, scope_kind_code, corporate_entity_id) "
                "values (%s, 'analysis_scope_all_visible', %s)",
                (visible_run, entity_id),
            )


def test_status_history_enforces_shape_order_time_and_legal_transitions(
    registry_db,
) -> None:
    """Append-only status evidence is a serialized state machine."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        first_run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="first-status",
        )
        _insert_all_visible_scope(cursor, first_run_id)
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
        _insert_all_visible_scope(cursor, second_run_id)
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="immutable-run",
        )
        _insert_all_visible_scope(cursor, run_id)
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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
        _insert_all_visible_scope(cursor, run_id)
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

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
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
        _insert_all_visible_scope(cursor, run_id)
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


def test_pending_may_cancel_and_running_may_fail(registry_db) -> None:
    """Legal non-success terminals are pending→cancelled and running→failed."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        cancelled_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="cancel-pending",
        )
        _insert_all_visible_scope(cursor, cancelled_id)
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z')",
            (cancelled_id,),
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 2, 'analysis_status_cancelled', "
            "'2026-08-15T01:00:01Z')",
            (cancelled_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 3, 'analysis_status_running', "
                "'2026-08-15T01:00:02Z')",
                (cancelled_id,),
            )

        failed_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="fail-running",
        )
        _insert_all_visible_scope(cursor, failed_id)
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at,
                 failure_code, retryable)
            values
                (%s, 1, 'analysis_status_pending', '2026-08-15T01:00:00Z',
                 null, false),
                (%s, 2, 'analysis_status_running', '2026-08-15T01:00:01Z',
                 null, false),
                (%s, 3, 'analysis_status_failed', '2026-08-15T01:00:02Z',
                 'tepp_unavailable', false)
            """,
            (failed_id, failed_id, failed_id),
        )
        cursor.execute(
            "select status_code from analysis_run_current_status "
            "where analysis_run_id = %s",
            (failed_id,),
        )
        assert cursor.fetchone()[0] == "analysis_status_failed"


def test_rollback_refuses_data_loss_then_removes_an_empty_registry(registry_db) -> None:
    """Downgrade fails closed until audit evidence is explicitly removed."""

    connection, _dsn = registry_db
    rollback_sql = _REGISTRY_ROLLBACK.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(rollback_sql)
        cursor.execute("rollback")
    with connection.cursor() as cursor:
        cursor.execute(
            "delete from analysis_source_snapshot "
            "where analysis_source_snapshot_id = %s",
            (snapshot_id,),
        )
        cursor.execute(rollback_sql)
        cursor.execute("select to_regclass('public.analysis_run')")
        assert cursor.fetchone()[0] is None
        cursor.execute(rollback_sql)
        _apply_sql_files(connection, [_REGISTRY_MIGRATION])
        cursor.execute("select to_regclass('public.analysis_run')")
        assert cursor.fetchone()[0] == "analysis_run"


def test_capture_after_request_and_availability_after_capture_are_rejected(
    registry_db,
) -> None:
    """The leakage guard rejects inverted snapshot and request clocks."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            _insert_snapshot(
                cursor,
                maximum_available_time="2026-08-15T00:10:00Z",
                captured_at="2026-08-15T00:05:00Z",
            )
        snapshot_id = _insert_snapshot(
            cursor,
            captured_at="2026-08-15T01:00:00Z",
        )
        account_id = _insert_account(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key="late-capture",
                requested_at="2026-08-15T00:45:00Z",
            )


def test_status_events_cannot_be_deleted(registry_db) -> None:
    """Append-only lifecycle evidence rejects delete as well as update."""

    connection, _dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="delete-status",
        )
        _insert_all_visible_scope(cursor, run_id)
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run_status_event "
                "where analysis_run_id = %s",
                (run_id,),
            )


def test_concurrent_count_writes_freeze_once_a_run_exists(registry_db) -> None:
    """Count insert and first run share the snapshot lock; later counts fail."""

    connection, dsn = registry_db
    with connection.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        cursor.execute(
            "insert into analysis_source_count values "
            "(%s, 'analysis_count_document', 3)",
            (snapshot_id,),
        )
        _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="freeze-race",
        )

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _race(count_type: str) -> None:
        raced = psycopg2.connect(dsn)
        raced.autocommit = True
        try:
            with raced.cursor() as cursor:
                barrier.wait(timeout=5)
                try:
                    cursor.execute(
                        "insert into analysis_source_count values (%s, %s, 1)",
                        (snapshot_id, count_type),
                    )
                    result = "inserted"
                except psycopg2.errors.RaiseException:
                    result = "frozen"
            with lock:
                outcomes.append(result)
        finally:
            raced.close()

    workers = [
        threading.Thread(target=_race, args=("analysis_count_thread",)),
        threading.Thread(target=_race, args=("analysis_count_source_row",)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)
    assert outcomes == ["frozen", "frozen"]
    with connection.cursor() as cursor:
        cursor.execute(
            "select count(*) from analysis_source_count "
            "where analysis_source_snapshot_id = %s",
            (snapshot_id,),
        )
        assert cursor.fetchone()[0] == 1

"""Contracts for the atomic analysis-run write (ADR 0017).

Pure digest/key tests always run. PostgreSQL tests self-skip without a
reachable administrator DSN, matching ``test_analysis_run_registry_schema``.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import psycopg2
import pytest
from psycopg2 import sql

from backend.app.analysis_run_write import (
    LINEAGE_RUN_KIND,
    LINEAGE_SCHEMA_VERSION,
    AnalysisRunConflict,
    AnalysisRunForbiddenScope,
    AnalysisRunInvalidRequest,
    AnalysisRunNotAllowed,
    AnalysisRunSnapshotMissing,
    _require_lineage_kind,
    canonical_idempotency_key,
    code_revision_digest,
    create_pending_lineage_run,
    parse_knowledge_cutoff,
    request_configuration_digest,
)

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)


def test_canonical_idempotency_key_rejects_padding_and_controls() -> None:
    """The product key must match the database trim/control contract."""
    assert canonical_idempotency_key("  retry-1  ") == "retry-1"
    with pytest.raises(AnalysisRunInvalidRequest):
        canonical_idempotency_key(" padded\nkey")
    with pytest.raises(AnalysisRunInvalidRequest):
        canonical_idempotency_key("")
    with pytest.raises(AnalysisRunInvalidRequest):
        canonical_idempotency_key("x" * 257)


def test_omitted_cutoff_is_stable_across_request_clocks() -> None:
    """Two retries a second apart must hash the same default cutoff."""
    first = datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc)
    second = datetime(2026, 8, 16, 15, 0, 1, tzinfo=timezone.utc)
    cutoff = datetime(2026, 1, 12, tzinfo=timezone.utc)
    left = request_configuration_digest(
        run_kind_code=LINEAGE_RUN_KIND,
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
        snapshot_sha256="a" * 64,
        knowledge_cutoff=cutoff,
        configuration_schema_version=LINEAGE_SCHEMA_VERSION,
    )
    right = request_configuration_digest(
        run_kind_code=LINEAGE_RUN_KIND,
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
        snapshot_sha256="a" * 64,
        knowledge_cutoff=cutoff,
        configuration_schema_version=LINEAGE_SCHEMA_VERSION,
    )
    assert left == right
    assert left != request_configuration_digest(
        run_kind_code=LINEAGE_RUN_KIND,
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
        snapshot_sha256="b" * 64,
        knowledge_cutoff=cutoff,
        configuration_schema_version=LINEAGE_SCHEMA_VERSION,
    )
    assert parse_knowledge_cutoff(None, requested_at=first) == first
    assert parse_knowledge_cutoff(None, requested_at=second) == second
    assert code_revision_digest() == code_revision_digest()


def test_tepp_and_report_kinds_are_rejected_without_a_fake_score() -> None:
    """This write path must not invent a TEPP theta or skip Reports."""
    with pytest.raises(AnalysisRunNotAllowed, match="does not invent a measurement"):
        _require_lineage_kind("analysis_run_tepp")
    with pytest.raises(AnalysisRunNotAllowed, match="Reports panel"):
        _require_lineage_kind("analysis_run_report")
    _require_lineage_kind(LINEAGE_RUN_KIND)


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


@pytest.fixture
def write_db():
    """Yield a throwaway registry database and its asyncpg DSN."""
    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    database_name = f"lineageweave_write_{uuid.uuid4().hex[:12]}"
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
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
            yield connection, dsn
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
        admin_connection.close()


def _seed_bound_snapshot(cursor) -> tuple[str, str]:
    """Insert one account, corp, snapshot, succeeded run, and return ids."""
    cursor.execute(
        """
        insert into user_account
            (external_subject_id, display_name, email_address)
        values (%s, 'Write User', %s)
        returning user_account_id
        """,
        (f"write-{uuid.uuid4().hex}", f"write-{uuid.uuid4().hex}@example.test"),
    )
    account_id = str(cursor.fetchone()[0])
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
        values (%s, 'Write Corp', 'company')
        returning corporate_entity_id
        """,
        (f"WRITE-{uuid.uuid4().hex[:8]}",),
    )
    corp_id = str(cursor.fetchone()[0])
    cursor.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, 'source-contract-v1',
                '2026-01-12T00:00:00Z', '2026-01-12T00:05:00Z')
        returning analysis_source_snapshot_id
        """,
        ("c" * 64,),
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
        values (%s, 'analysis_run_lineage', 'seed-write',
                %s, '2026-01-12T12:00:00Z', 'lineage-run-v1', %s, %s,
                '2026-01-12T12:30:00Z')
        returning analysis_run_id
        """,
        (snapshot_id, account_id, "b" * 64, "d" * 40),
    )
    run_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        """,
        (run_id, corp_id),
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
    return account_id, corp_id


def test_create_pending_run_replays_same_digest_and_conflicts_on_drift(write_db) -> None:
    """Same key + same snapshot digest replays; a drifted cutoff conflicts."""
    connection, dsn = write_db
    with connection.cursor() as cursor:
        account_id, corp_id = _seed_bound_snapshot(cursor)

    async def _exercise() -> None:
        conn = await asyncpg.connect(dsn)
        try:
            first = await create_pending_lineage_run(
                conn,
                account_id=account_id,
                affiliated_entity_ids=frozenset({corp_id}),
                run_kind_code=LINEAGE_RUN_KIND,
                idempotency_key="buyer-retry-1",
                corporate_entity_id=corp_id,
            )
            replay = await create_pending_lineage_run(
                conn,
                account_id=account_id,
                affiliated_entity_ids=frozenset({corp_id}),
                run_kind_code=LINEAGE_RUN_KIND,
                idempotency_key="buyer-retry-1",
                corporate_entity_id=corp_id,
            )
            assert first.analysis_run_id == replay.analysis_run_id
            assert first.replayed is False
            assert replay.replayed is True
            status = await conn.fetchval(
                """
                select status_code from analysis_run_current_status
                 where analysis_run_id = $1::uuid
                """,
                first.analysis_run_id,
            )
            assert status == "analysis_status_pending"
            with pytest.raises(AnalysisRunConflict):
                await create_pending_lineage_run(
                    conn,
                    account_id=account_id,
                    affiliated_entity_ids=frozenset({corp_id}),
                    run_kind_code=LINEAGE_RUN_KIND,
                    idempotency_key="buyer-retry-1",
                    corporate_entity_id=corp_id,
                    knowledge_cutoff="2026-01-12T12:00:00Z",
                )
            with pytest.raises(AnalysisRunForbiddenScope):
                await create_pending_lineage_run(
                    conn,
                    account_id=account_id,
                    affiliated_entity_ids=frozenset({corp_id}),
                    run_kind_code=LINEAGE_RUN_KIND,
                    idempotency_key="other-corp",
                    corporate_entity_id=str(uuid.uuid4()),
                )
            with pytest.raises(AnalysisRunSnapshotMissing):
                await create_pending_lineage_run(
                    conn,
                    account_id=account_id,
                    affiliated_entity_ids=frozenset({str(uuid.uuid4())}),
                    run_kind_code=LINEAGE_RUN_KIND,
                    idempotency_key="no-snapshot",
                )
        finally:
            await conn.close()

    asyncio.run(_exercise())

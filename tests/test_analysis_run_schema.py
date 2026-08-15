"""Real-PostgreSQL tests for migration 0018's 3NF provenance contract."""

from __future__ import annotations

import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_INITIAL = _ROOT / "migrations" / "0001_initial_schema.sql"
_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_provenance.sql"


def _postgres_available() -> bool:
    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def analysis_db():
    """Create a database containing the initial and analysis-run schemas."""

    database_name = f"lineageweave_analysis_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    try:
        parsed = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed._replace(path=f"/{database_name}"))
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL.read_text(encoding="utf-8"))
                cursor.execute(_MIGRATION.read_text(encoding="utf-8"))
            connection.commit()
            yield connection
        finally:
            connection.close()
    finally:
        with admin.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin.close()


def _seed_account(connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into user_account (external_subject_id, display_name, email_address) "
            "values ('analysis-subject', 'Analysis Operator', 'analysis@example.test') "
            "returning user_account_id"
        )
        return str(cursor.fetchone()[0])


def test_analysis_schema_applies_and_persists_normalized_run(analysis_db) -> None:
    account_id = _seed_account(analysis_db)
    digest_a = "a" * 64
    digest_b = "b" * 64
    with analysis_db.cursor() as cursor:
        cursor.execute(
            "insert into analysis_source_profile ("
            "source_profile_key, profile_revision, source_kind_code, query_digest_sha256"
            ") values ('configured-primary', 1, 'postgresql_query_profile', %s) "
            "returning source_profile_id",
            (digest_a,),
        )
        profile_id = cursor.fetchone()[0]
        cursor.execute(
            "insert into analysis_source_snapshot ("
            "source_profile_id, source_digest_sha256, knowledge_cutoff, "
            "maximum_available_time, row_count, document_count, thread_count"
            ") values (%s, %s, '2026-08-15T00:00:00Z', "
            "'2026-08-14T23:59:00Z', 12, 10, 8) returning source_snapshot_id",
            (profile_id, digest_b),
        )
        snapshot_id = cursor.fetchone()[0]
        cursor.execute(
            "insert into analysis_run_record ("
            "source_snapshot_id, requested_by_account_id, run_status_code, "
            "idempotency_key, request_digest_sha256, started_at"
            ") values (%s, %s, 'analysis_run_running', 'run-key', %s, now()) "
            "returning analysis_run_id",
            (snapshot_id, account_id, digest_a),
        )
        run_id = cursor.fetchone()[0]
        cursor.execute(
            "insert into analysis_run_configuration values "
            "(%s, 0, true, true, true, 'tepp-v1', 'aggregate')",
            (run_id,),
        )
        cursor.execute(
            "insert into analysis_service_run ("
            "analysis_run_id, service_kind_code, service_status_code, "
            "remote_run_identifier, idempotency_key, request_digest_sha256, "
            "started_at"
            ") values (%s, 'analysis_service_tepp', 'analysis_service_running', "
            "'remote-run', 'service-key', %s, now())",
            (run_id, digest_b),
        )
        cursor.execute(
            "insert into analysis_artifact_record ("
            "analysis_run_id, artifact_kind_code, artifact_reference_uri, "
            "content_digest_sha256, byte_count"
            ") values (%s, 'analysis_aggregate_manifest', "
            "'urn:lineageweave:artifact:aggregate', %s, 512)",
            (run_id, digest_a),
        )
        cursor.execute(
            "select count(*) from analysis_run_record where analysis_run_id = %s",
            (run_id,),
        )
        assert cursor.fetchone()[0] == 1
    analysis_db.commit()


def test_snapshot_rejects_future_information_leakage(analysis_db) -> None:
    with analysis_db.cursor() as cursor:
        cursor.execute(
            "insert into analysis_source_profile ("
            "source_profile_key, profile_revision, source_kind_code, query_digest_sha256"
            ") values ('configured-secondary', 1, 'postgresql_query_profile', %s) "
            "returning source_profile_id",
            ("a" * 64,),
        )
        profile_id = cursor.fetchone()[0]
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_source_snapshot ("
                "source_profile_id, source_digest_sha256, knowledge_cutoff, "
                "maximum_available_time, row_count, document_count, thread_count"
                ") values (%s, %s, '2026-08-15T00:00:00Z', "
                "'2026-08-15T00:00:01Z', 1, 1, 1)",
                (profile_id, "b" * 64),
            )
    analysis_db.rollback()


def test_profile_revision_and_digest_contracts_are_database_enforced(analysis_db) -> None:
    with analysis_db.cursor() as cursor:
        cursor.execute(
            "insert into analysis_source_profile ("
            "source_profile_key, profile_revision, source_kind_code, query_digest_sha256"
            ") values ('configured-unique', 1, 'postgresql_query_profile', %s)",
            ("a" * 64,),
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute(
                "insert into analysis_source_profile ("
                "source_profile_key, profile_revision, source_kind_code, query_digest_sha256"
                ") values ('configured-unique', 1, 'postgresql_query_profile', %s)",
                ("b" * 64,),
            )
    analysis_db.rollback()
    with analysis_db.cursor() as cursor:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_source_profile ("
                "source_profile_key, profile_revision, source_kind_code, query_digest_sha256"
                ") values ('configured-bad', 1, 'postgresql_query_profile', 'NOT-A-DIGEST')"
            )
    analysis_db.rollback()


def test_new_database_object_names_follow_two_word_snake_case_rule() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    names = re.findall(r"create table (\w+)", sql)
    assert names
    for name in names:
        assert re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", name), name

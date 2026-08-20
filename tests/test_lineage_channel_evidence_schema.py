"""Real-PostgreSQL rehearsal for versioned Event Lineage evidence schema."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN",
    "postgresql://localhost/postgres",
)
_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_SCHEMA = _ROOT / "migrations" / "0001_initial_schema.sql"
_MIGRATION = _ROOT / "migrations" / "0053_lineage_edge_channel_score.sql"
_ROLLBACK = (
    _ROOT / "migrations" / "rollback" / "0053_lineage_edge_channel_score.sql"
)


def _postgres_available() -> bool:
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def evidence_schema_db():
    """Yield a throwaway database after clean install and repeat migration."""

    database_name = f"lineageweave_evidence_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    try:
        parsed = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed._replace(path=f"/{database_name}"))
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_SCHEMA.read_text(encoding="utf-8"))
                cursor.execute(_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_MIGRATION.read_text(encoding="utf-8"))
            connection.commit()
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin_connection.close()


def test_migration_reapplies_and_creates_normalized_authority(evidence_schema_db) -> None:
    with evidence_schema_db.cursor() as cursor:
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name like 'lineage_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "select column_name from information_schema.columns "
            "where table_name = 'post_lineage_edge'"
        )
        edge_columns = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "select lookup_code from common_lookup_value "
            "where lookup_category = 'lineage_channel' order by display_order"
        )
        channel_codes = [row[0] for row in cursor.fetchall()]

    assert {
        "lineage_reconstruction_run",
        "lineage_reconstruction_run_channel",
        "lineage_edge_channel_score",
    } <= tables
    assert "lineage_reconstruction_run_id" in edge_columns
    assert channel_codes == [
        "lineage_channel_temporal",
        "lineage_channel_secondary_key",
        "lineage_channel_text",
        "lineage_channel_llm",
    ]


def test_schema_rejects_invalid_weight_contribution_and_orphan_signal(
    evidence_schema_db,
) -> None:
    run_id = str(uuid.uuid4())
    with evidence_schema_db.cursor() as cursor:
        cursor.execute(
            "insert into lineage_reconstruction_run "
            "(lineage_reconstruction_run_id, reconstruction_version) "
            "values (%s, 'schema-test-v1')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into lineage_reconstruction_run_channel "
                "(lineage_reconstruction_run_id, channel_code, channel_weight) "
                "values (%s, 'lineage_channel_text', 0)",
                (run_id,),
            )
    evidence_schema_db.rollback()

    with evidence_schema_db.cursor() as cursor:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cursor.execute(
                "insert into lineage_edge_channel_score "
                "(parent_post_id, child_post_id, channel_code, channel_score, "
                "channel_contribution) values (%s, %s, "
                "'lineage_channel_text', 0.5, 0.5)",
                (str(uuid.uuid4()), str(uuid.uuid4())),
            )
    evidence_schema_db.rollback()

    with evidence_schema_db.cursor() as cursor:
        cursor.execute(
            "insert into lineage_reconstruction_run "
            "(lineage_reconstruction_run_id, reconstruction_version) "
            "values (%s, 'schema-test-v2')",
            (run_id,),
        )
        cursor.execute(
            "insert into lineage_reconstruction_run_channel "
            "(lineage_reconstruction_run_id, channel_code, channel_weight) "
            "values (%s, 'lineage_channel_text', 1)",
            (run_id,),
        )
        cursor.execute(
            "insert into common_lookup_value "
            "(lookup_category, lookup_code, lookup_label) values "
            "('corporate_entity_level', 'schema_group', 'Group'), "
            "('post_visibility', 'schema_public', 'Public'), "
            "('voc_type', 'schema_voc', 'Voice of Customer')"
        )
        cursor.execute(
            "insert into corporate_entity "
            "(corporate_entity_code, entity_name, entity_level_code) "
            "values ('SCHEMA-CORP', 'Schema Corp', 'schema_group') "
            "returning corporate_entity_id"
        )
        corporate_entity_id = cursor.fetchone()[0]
        cursor.execute(
            "insert into user_account "
            "(external_subject_id, display_name, email_address) "
            "values ('schema-user', 'Schema User', 'schema@example.test') "
            "returning user_account_id"
        )
        account_id = cursor.fetchone()[0]
        post_ids = []
        for title in ("Parent", "Child"):
            cursor.execute(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, post_title, post_body, "
                "voc_type_code, visibility_code) values (%s, %s, %s, 'body', "
                "'schema_voc', 'schema_public') returning post_id",
                (account_id, corporate_entity_id, title),
            )
            post_ids.append(cursor.fetchone()[0])
        cursor.execute(
            "insert into post_lineage_edge "
            "(parent_post_id, child_post_id, fused_score, "
            "lineage_reconstruction_run_id) values (%s, %s, 0.5, %s)",
            (post_ids[0], post_ids[1], run_id),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into lineage_edge_channel_score "
                "(parent_post_id, child_post_id, channel_code, channel_score, "
                "channel_contribution) values (%s, %s, "
                "'lineage_channel_text', 0.5, 1.1)",
                (post_ids[0], post_ids[1]),
            )
    evidence_schema_db.rollback()


def test_rollback_removes_only_lineage_evidence_extension(evidence_schema_db) -> None:
    with evidence_schema_db.cursor() as cursor:
        cursor.execute(_ROLLBACK.read_text(encoding="utf-8"))
    evidence_schema_db.commit()

    with evidence_schema_db.cursor() as cursor:
        cursor.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name in ("
            "'lineage_reconstruction_run', "
            "'lineage_reconstruction_run_channel', "
            "'lineage_edge_channel_score')"
        )
        assert cursor.fetchall() == []
        cursor.execute(
            "select column_name from information_schema.columns "
            "where table_name = 'post_lineage_edge' "
            "and column_name = 'lineage_reconstruction_run_id'"
        )
        assert cursor.fetchone() is None
        cursor.execute("select to_regclass('public.post_lineage_edge')")
        assert cursor.fetchone()[0] == "post_lineage_edge"

"""Real-database test for migrations/0001_initial_schema.sql.

Applies the actual migration file (not a re-typed copy of it) to a
throwaway PostgreSQL database, then proves two concrete things the
schema is supposed to guarantee: a real-shaped corporate hierarchy query
returns the right shape, and an invalid lookup code is genuinely rejected
by a foreign key, not just documented as an intention.

Skipped unless a local PostgreSQL server is reachable (LINEAGEWEAVE_TEST_
POSTGRES_DSN, defaulting to the conventional local superuser DSN) --
CI without a database available stays green; this is meant to be run
with a real Postgres, same spirit as the real-provider LLM tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import psycopg2
import psycopg2.errors
import pytest

from backend.app.post_chat_ingestion import gather_global_chat_sources
from scripts.import_onet_ratings import import_ratings

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "0001_initial_schema.sql"
_MAJOR_EVENT_ACTION_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0100_major_event_action.sql"
)
_PROJECT_MENTION_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0031_semantic_project_mentions.sql"
)
_POST_CONTENT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0026_post_content_artifacts.sql"
)
_SOURCE_STATE_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0033_source_state_provenance.sql"
)
_SOURCE_CONTEXT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0034_source_context_provenance.sql"
)
_SOURCE_IDENTITY_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0037_source_record_identity.sql"
)
_SOURCE_NAMED_HINTS_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0038_source_named_hints.sql"
)
_SOURCE_ORG_HINTS_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0039_source_org_named_hints.sql"
)
_SOURCE_EVENT_TIME_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0183_source_post_event_occurred_at.sql"
)
_PROJECT_BOUND_ACTION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0101_project_bound_major_event_action.sql"
)
_PROJECT_BOUND_EVENT_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0102_project_bound_summary_event.sql"
)
_INTERVAL_RELATION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0140_post_lineage_interval_relation.sql"
)
_LEFTOVER_OBSERVED_EXPECTED_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0163_report_leftover_observed_expected.sql"
)
_LEFTOVER_MAP_RANK_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0164_report_leftover_map_rank.sql"
)
_LEFTOVER_MAP_CROSS_SHARE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0185_report_leftover_map_cross_share.sql"
)
_LEFTOVER_MAP_RECONSTRUCTION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0206_report_leftover_map_reconstruction.sql"
)
_LEFTOVER_MAP_AXIS_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0169_report_leftover_map_axis.sql"
)
_GLOBAL_ASK_EVIDENCE_SEARCH_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0210_global_ask_evidence_search_indexes.sql"
)
_ONET_RATING_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0222_onet_rating_observation_store.sql"
)
_CHANNEL_EVIDENCE_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0174_post_lineage_edge_signal.sql"
)
_LEFTOVER_MAP_COVERAGE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0168_report_leftover_map_coverage.sql"
)
_LEFTOVER_MAP_UNEXPLAINED_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0182_report_leftover_map_unexplained.sql"
)


def _postgres_available() -> bool:
    try:
        conn = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)",
)


@pytest.fixture
def schema_db():
    """A freshly migrated, throwaway database, dropped afterward."""
    db_name = f"lineageweave_test_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f'create database "{db_name}"')
    try:
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        db_dsn = urlunsplit(parsed_admin_dsn._replace(path=f"/{db_name}"))
        conn = psycopg2.connect(db_dsn)
        # Production migration runs each file through psql -X, so concurrent
        # indexes are outside a transaction. Keep this integration fixture's
        # execution semantics identical to that path.
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(_MIGRATION_PATH.read_text())
                cur.execute(_POST_CONTENT_MIGRATION.read_text())
                cur.execute(_PROJECT_MENTION_MIGRATION.read_text())
                cur.execute(_SOURCE_STATE_MIGRATION.read_text())
                cur.execute(_SOURCE_CONTEXT_MIGRATION.read_text())
                cur.execute("create extension if not exists pg_trgm")
                cur.execute(_SOURCE_IDENTITY_MIGRATION.read_text())
                cur.execute(_SOURCE_NAMED_HINTS_MIGRATION.read_text())
                cur.execute(_SOURCE_ORG_HINTS_MIGRATION.read_text())
                cur.execute(_MAJOR_EVENT_ACTION_MIGRATION.read_text())
                cur.execute(_PROJECT_BOUND_ACTION_MIGRATION.read_text())
                cur.execute(_PROJECT_BOUND_EVENT_MIGRATION.read_text())
                cur.execute(_INTERVAL_RELATION_MIGRATION.read_text())
                cur.execute(_LEFTOVER_OBSERVED_EXPECTED_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_RANK_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_COVERAGE_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_AXIS_MIGRATION.read_text())
                cur.execute(_CHANNEL_EVIDENCE_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_UNEXPLAINED_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_CROSS_SHARE_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_RECONSTRUCTION_MIGRATION.read_text())
                cur.execute(_SOURCE_EVENT_TIME_MIGRATION.read_text())
                cur.execute(_ONET_RATING_MIGRATION.read_text())
                # psql sends each statement independently, which is required
                # by CREATE INDEX CONCURRENTLY. psycopg2 treats a multi-
                # statement execute as one transaction even with autocommit.
                for statement in _GLOBAL_ASK_EVIDENCE_SEARCH_MIGRATION.read_text().split(";\n\n"):
                    if statement.strip():
                        cur.execute(statement + ";")
            # Migration replay needs autocommit for concurrent indexes, while
            # tests need transactions for savepoints and rollback assertions.
            conn.autocommit = False
            yield conn
        finally:
            conn.close()
    finally:
        with admin_conn.cursor() as cur:
            cur.execute(f'drop database "{db_name}"')
        admin_conn.close()


def test_migration_applies_cleanly(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            "select table_name from information_schema.tables where table_schema = 'public' order by table_name"
        )
        tables = {row[0] for row in cur.fetchall()}
    expected = {
        "common_lookup_value",
        "corporate_entity",
        "process_unit",
        "user_account",
        "account_affiliation",
        "access_role",
        "role_permission",
        "account_role_assignment",
        "abac_policy",
        "source_post",
        "post_counterparty_entity",
        "post_project_mention",
        "cataloged_person",
        "person_affiliation",
        "post_person_mention",
        "post_summary_person_mention",
        "knowledge_graph_edge",
        "knowledge_graph_edge_evidence",
        "issue_ticket",
        "post_lineage_edge",
        "post_lineage_edge_signal",
        "event_lineage_rebuild",
        "event_lineage_rebuild_channel",
        "post_evaluation_response",
        "report_period_score",
        "report_member_score",
        "report_item_parameter",
        "report_item_information",
        "report_leftover_pair",
        "report_leftover_map_axis",
        "report_leftover_map_coverage",
        "post_summary_result",
        "post_summary_event",
        "post_summary_role",
        "post_summary_action",
        "post_chat_result",
        "post_chat_citation",
        "occupational_data_release",
        "occupational_source_table",
        "occupational_scale_definition",
        "occupational_classification_entry",
        "occupational_element_definition",
        "occupational_rating_observation",
    }
    assert expected <= tables


def test_onet_rating_store_partitions_upserts_and_rejects_invalid_error(schema_db) -> None:
    """Persist one realistic rating without collapsing missing category or uncertainty."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            insert into occupational_data_release
                (data_release_code, release_version, source_publisher_name, source_license_url)
            values ('onet-31.0', '31.0', 'National Center for O*NET Development',
                    'https://creativecommons.org/licenses/by/4.0/')
            """
        )
        cur.execute(
            """
            insert into occupational_source_table
                (data_release_code, source_table_code, source_table_name,
                 source_artifact_url, source_artifact_sha256, source_row_count)
            values ('onet-31.0', 'abilities', 'Abilities', 'https://example.test/abilities.json',
                    %s, 94640)
            """,
            ("a" * 64,),
        )
        cur.execute(
            """
            insert into occupational_source_table
                (data_release_code, source_table_code, source_table_name,
                 source_artifact_url, source_artifact_sha256, source_row_count)
            values ('onet-31.0', 'scales_reference', 'Scales Reference',
                    'https://example.test/scales-reference.json', %s, 33)
            """,
            ("b" * 64,),
        )
        cur.execute(
            """
            insert into occupational_source_table
                (data_release_code, source_table_code, source_table_name,
                 source_artifact_url, source_artifact_sha256, source_row_count)
            values ('onet-31.0', 'work_context', 'Work Context',
                    'https://example.test/work-context.json', %s, 305389)
            """,
            ("c" * 64,),
        )
        cur.execute(
            """
            insert into occupational_scale_definition
                (data_release_code, source_table_code, scale_id, scale_name,
                 minimum_value, maximum_value)
            values ('onet-31.0', 'scales_reference', 'IM', 'Importance', 1, 5)
            """
        )
        cur.execute(
            """
            insert into occupational_scale_definition
                (data_release_code, source_table_code, scale_id, scale_name,
                 minimum_value, maximum_value)
            values ('onet-31.0', 'scales_reference', 'CXP',
                    'Context (Categories 1-5)', 0, 100)
            """
        )
        cur.execute(
            """
            insert into occupational_classification_entry
                (data_release_code, onetsoc_code, occupation_title)
            values ('onet-31.0', '15-1252.00', 'Synthetic software occupation')
            """
        )
        cur.execute(
            """
            insert into occupational_element_definition
                (data_release_code, element_id, element_name)
            values ('onet-31.0', '1.A.1.a.1', 'Oral Comprehension')
            """
        )
        cur.execute(
            """
            insert into occupational_element_definition
                (data_release_code, element_id, element_name)
            values ('onet-31.0', '4.C.1.a.2.f', 'Telephone Conversations')
            """
        )
        cur.execute("savepoint missing_partition")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                insert into occupational_rating_observation
                    (data_release_code, source_table_code, onetsoc_code, element_id,
                     scale_id, data_value, source_updated_month, domain_source_code)
                values ('onet-31.0', 'abilities', '15-1252.00', '1.A.1.a.1',
                        'IM', 4.10, '08/2026', 'Analyst')
                """
            )
        cur.execute("rollback to savepoint missing_partition")
        cur.execute(
            """
            create table occupational_rating_observation_onet_31
                partition of occupational_rating_observation
                for values in ('onet-31.0') partition by list (source_table_code)
            """
        )
        cur.execute(
            """
            create table occupational_rating_observation_onet_31_abilities
                partition of occupational_rating_observation_onet_31
                for values in ('abilities')
            """
        )
        cur.execute(
            """
            create table occupational_rating_observation_onet_31_work_context
                partition of occupational_rating_observation_onet_31
                for values in ('work_context')
            """
        )
        cur.execute(
            """
            insert into occupational_rating_observation
                (data_release_code, source_table_code, onetsoc_code, element_id,
                 scale_id, category_value, data_value, source_updated_month,
                 domain_source_code)
            values ('onet-31.0', 'work_context', '15-1252.00', '4.C.1.a.2.f',
                    'CXP', 5, 63.25, '08/2026', 'Incumbent')
            """
        )
        cur.execute(
            """
            select category_value, data_value
              from occupational_rating_observation
             where scale_id = 'CXP'
            """
        )
        assert cur.fetchone() == (5, Decimal("63.25"))
        cur.execute("savepoint cxp_outside_percentage")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                insert into occupational_rating_observation
                    (data_release_code, source_table_code, onetsoc_code, element_id,
                     scale_id, category_value, data_value, source_updated_month,
                     domain_source_code)
                values ('onet-31.0', 'work_context', '15-1252.00', '4.C.1.a.2.f',
                        'CXP', 4, 100.01, '08/2026', 'Incumbent')
                """
            )
        cur.execute("rollback to savepoint cxp_outside_percentage")
        statement = """
            insert into occupational_rating_observation
                (data_release_code, source_table_code, onetsoc_code, element_id,
                 scale_id, category_value, data_value, sample_size, standard_error,
                 lower_ci_bound, upper_ci_bound, recommend_suppress, not_relevant,
                 source_updated_month, domain_source_code)
            values ('onet-31.0', 'abilities', '15-1252.00', '1.A.1.a.1',
                    'IM', null, %s, 120, 0.08, 3.94, 4.26, false, false,
                    '08/2026', 'Analyst')
            on conflict on constraint occupational_rating_identity_key
            do nothing
        """
        cur.execute(statement, (4.10,))
        cur.execute("savepoint divergent_duplicate")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(statement, (4.25,))
        cur.execute("rollback to savepoint divergent_duplicate")
        cur.execute(statement, (4.10,))
        cur.execute(
            """
            select count(*), max(data_value), max(source_updated_month)
            from occupational_rating_observation
            where data_release_code = 'onet-31.0' and scale_id = 'IM'
            """
        )
        assert cur.fetchone() == (1, Decimal("4.10"), "08/2026")
        cur.execute("savepoint immutable_update")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                update occupational_rating_observation
                set data_value = 4.25
                where data_release_code = 'onet-31.0'
                """
            )
        cur.execute("rollback to savepoint immutable_update")
        cur.execute("savepoint immutable_delete")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "delete from occupational_rating_observation where data_release_code = 'onet-31.0'"
            )
        cur.execute("rollback to savepoint immutable_delete")
        cur.execute("savepoint immutable_truncate")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute("truncate occupational_rating_observation")
        cur.execute("rollback to savepoint immutable_truncate")
        for savepoint, value_sql, month_sql in (
            ("outside_scale", "6.00", "'08/2026'"),
            (
                "future_source_month",
                "4.00",
                "to_char(current_date + interval '1 month', 'MM/YYYY')",
            ),
            ("malformed_source_month", "4.00", "'13/2026'"),
        ):
            cur.execute(f"savepoint {savepoint}")
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(
                    f"""
                    insert into occupational_rating_observation
                        (data_release_code, source_table_code, onetsoc_code, element_id,
                         scale_id, category_value, data_value, source_updated_month,
                         domain_source_code)
                    values ('onet-31.0', 'abilities', '15-1252.00', '1.A.1.a.1',
                            'IM', 1, {value_sql}, {month_sql}, 'Analyst')
                    """
                )
            cur.execute(f"rollback to savepoint {savepoint}")
        cur.execute("savepoint invalid_standard_error")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                insert into occupational_rating_observation
                    (data_release_code, source_table_code, onetsoc_code, element_id,
                     scale_id, category_value, data_value, standard_error,
                     source_updated_month, domain_source_code)
                values ('onet-31.0', 'abilities', '15-1252.00', '1.A.1.a.1',
                        'IM', 2, 4.00, -0.01, '08/2026', 'Analyst')
                """
            )
        cur.execute("rollback to savepoint invalid_standard_error")


def test_onet_rating_importer_is_idempotent_against_postgresql(
    schema_db,
    tmp_path: Path,
) -> None:
    """A pinned synthetic artifact imports twice as one exact observation."""
    scales = tmp_path / "scales.csv"
    scales.write_text(
        "Scale ID,Scale Name,Minimum,Maximum\nIM,Importance,1,5\n",
        encoding="utf-8",
    )
    ratings = tmp_path / "abilities.csv"
    ratings.write_text(
        "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Not Relevant,Date,Domain Source\n"
        "15-1252.00,Synthetic occupation,1.A.1.a.1,Oral Comprehension,IM,Importance,4.10,120,0.08,3.94,4.26,N,,08/2026,Analyst\n",
        encoding="utf-8",
    )
    args = SimpleNamespace(
        target_dsn=urlunsplit(
            urlsplit(_ADMIN_DSN)._replace(path=f"/{schema_db.info.dbname}")
        ),
        release_code="onet-31.0-synthetic",
        release_version="31.0-synthetic",
        source_table_code="abilities",
        source_table_name="Abilities",
        source_url="https://example.test/abilities.csv",
        source_sha256=hashlib.sha256(ratings.read_bytes()).hexdigest(),
        source_row_count=1,
        publisher="Synthetic publisher",
        license_url="https://example.test/license",
        scales_file=scales,
        scales_url="https://example.test/scales.csv",
        scales_sha256=hashlib.sha256(scales.read_bytes()).hexdigest(),
        scales_row_count=1,
        ratings_file=ratings,
    )

    assert asyncio.run(import_ratings(args))["imported_rows"] == 1
    assert asyncio.run(import_ratings(args))["imported_rows"] == 1
    with schema_db.cursor() as cur:
        cur.execute(
            """select count(*), min(data_value), bool_or(not_relevant is null)
                 from occupational_rating_observation
                where data_release_code = 'onet-31.0-synthetic'"""
        )
        assert cur.fetchone() == (1, Decimal("4.10"), True)


def test_global_ask_evidence_search_indexes_exist_on_normalized_tables(schema_db) -> None:
    """The real PostgreSQL schema owns all nine evidence-search indexes."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select indexname
              from pg_indexes
             where schemaname = 'public'
               and (indexname like '%_evidence_search_idx'
                    or indexname = 'knowledge_graph_edge_type_search_idx')
             order by indexname
            """
        )
        index_names = [row[0] for row in cur.fetchall()]

    assert index_names == [
        "cataloged_person_evidence_search_idx",
        "cataloged_team_evidence_search_idx",
        "common_lookup_value_evidence_search_idx",
        "corporate_entity_evidence_search_idx",
        "knowledge_graph_edge_type_search_idx",
        "person_affiliation_evidence_search_idx",
        "post_project_mention_evidence_search_idx",
        "post_summary_role_evidence_search_idx",
        "source_post_title_evidence_search_idx",
    ]


def test_global_ask_nominates_a_live_semantic_only_post(schema_db) -> None:
    """Real PostgreSQL retrieves a post whose query term exists only in evidence."""
    post_id = "30000000-0000-0000-0000-000000000001"
    with schema_db.cursor() as cur:
        cur.execute(
            """
            insert into common_lookup_value
                (lookup_category, lookup_code, lookup_label)
            values
                ('corporate_entity_level', 'semantic_test_level', 'Synthetic level'),
                ('voc_type', 'semantic_test_voc', 'Synthetic VOC'),
                ('post_visibility', 'semantic_test_public', 'Synthetic public'),
                ('person_side', 'semantic_test_person_side', 'Synthetic person side'),
                ('node_type', 'node_person', 'Person'),
                ('node_type', 'node_corporate_entity', 'Corporate entity'),
                ('edge_type', 'edge_affiliation', 'Affiliated with')
            """
        )
        cur.execute(
            """
            insert into corporate_entity
                (corporate_entity_id, corporate_entity_code, entity_name,
                 entity_level_code)
            values
                ('10000000-0000-0000-0000-000000000001', 'SYNTH-CORP',
                 'Synthetic Corp', 'semantic_test_level')
            """
        )
        cur.execute(
            """
            insert into user_account
                (user_account_id, external_subject_id, display_name, email_address)
            values
                ('20000000-0000-0000-0000-000000000001', 'synthetic-subject',
                 'Synthetic User', 'synthetic@example.invalid')
            """
        )
        cur.execute(
            """
            insert into source_post
                (post_id, author_account_id, corporate_entity_id, post_title,
                 post_body, voc_type_code, visibility_code)
            values
                (%s, '20000000-0000-0000-0000-000000000001',
                 '10000000-0000-0000-0000-000000000001', 'Neutral title',
                 'Neutral body', 'semantic_test_voc', 'semantic_test_public')
            """,
            (post_id,),
        )
        cur.execute(
            """
            insert into post_project_mention
                (post_id, project_key, project_name, evidence_text, confidence,
                 ontology_iri, extraction_method)
            values
                (%s, 'semantic-project', 'Exclusive Semantic Project',
                 'Synthetic project evidence', 1.000,
                 'https://contextualwisdomlab.github.io/LineageWeave/ontology#Project',
                 'synthetic_test')
            """,
            (post_id,),
        )
        cur.execute(
            """
            insert into cataloged_person
                (person_id, person_name, person_side_code, last_known_job_title)
            values
                ('40000000-0000-0000-0000-000000000001', 'Synthetic Expert',
                 'semantic_test_person_side', 'Synthetic Reviewer')
            """
        )
        cur.execute(
            """
            insert into person_affiliation
                (person_id, affiliated_organization_name,
                 affiliated_corporate_entity_id, role_title)
            values
                ('40000000-0000-0000-0000-000000000001', 'Synthetic Corp',
                 '10000000-0000-0000-0000-000000000001', 'Synthetic Reviewer')
            """
        )
        cur.execute(
            """
            insert into post_person_mention (post_id, person_id, mention_context)
            values (%s, '40000000-0000-0000-0000-000000000001', 'Synthetic evidence')
            """,
            (post_id,),
        )
        cur.execute(
            """
            insert into knowledge_graph_edge
                (knowledge_graph_edge_id, source_node_type_code, source_node_id,
                 target_node_type_code, target_node_id, edge_type_code)
            values
                ('50000000-0000-0000-0000-000000000001', 'node_person',
                 '40000000-0000-0000-0000-000000000001',
                 'node_corporate_entity',
                 '10000000-0000-0000-0000-000000000001', 'edge_affiliation')
            """
        )
    schema_db.commit()
    async_dsn = urlunsplit(
        urlsplit(_ADMIN_DSN)._replace(path=f"/{schema_db.info.dbname}")
    )

    async def retrieve(question: str) -> list:
        # Reuse the fixture DSN so password-authenticated CI databases keep
        # the same credentials as the psycopg2 migration connection.
        conn = await asyncpg.connect(async_dsn)
        try:
            return await gather_global_chat_sources(
                conn,
                lambda row: row["visibility_code"] == "semantic_test_public",
                ["10000000-0000-0000-0000-000000000001"],
                question=question,
                question_embedding=([1.0, 0.0], "synthetic-model", 1.0),
                limit=4,
            )
        finally:
            await conn.close()

    sources = asyncio.run(retrieve("Exclusive Semantic Project"))

    assert [source.post_id for source in sources] == [post_id]
    assert any(
        "Exclusive Semantic Project" in fact for fact in sources[0].evidence_facts
    )
    assert [source.post_id for source in asyncio.run(retrieve("Synthetic Expert"))] == [
        post_id
    ]
    assert [
        source.post_id
        for source in asyncio.run(
            retrieve(
                "https://contextualwisdomlab.github.io/LineageWeave/ontology#affiliatedWith"
            )
        )
    ] == [post_id]


def test_post_lineage_edge_requires_an_allen_interval_code(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select is_nullable
              from information_schema.columns
             where table_name = 'post_lineage_edge'
               and column_name = 'interval_relation_code'
            """
        )
        assert cur.fetchone()[0] == "NO"
        cur.execute(
            "select lookup_code from common_lookup_value "
            "where lookup_category = 'interval_relation' order by display_order"
        )
        codes = [row[0] for row in cur.fetchall()]
    assert "interval_contains" in codes
    assert "interval_overlaps" in codes
    assert len(codes) == 13


def test_major_event_action_project_reference_is_normalized(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select confrelid::regclass::text
              from pg_constraint
             where conname = 'post_summary_action_project_mention_fk'
            """
        )
        assert cur.fetchone()[0] == "post_project_mention"


def test_summary_event_project_reference_is_normalized(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select confrelid::regclass::text
              from pg_constraint
             where conname = 'post_summary_event_project_mention_fk'
            """
        )
        assert cur.fetchone()[0] == "post_project_mention"


def test_leftover_pair_references_member_and_item_rows(schema_db) -> None:
    """A leftover pair cannot name a post or item from another report."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select confrelid::regclass::text
            from pg_constraint
            where conrelid = 'report_leftover_pair'::regclass and contype = 'f'
            """
        )
        targets = {row[0] for row in cur.fetchall()}
    assert "report_member_score" in targets
    assert "report_item_information" in targets
    assert "report_period_score" in targets


def test_lineage_channel_evidence_is_cascaded_and_lookup_controlled(schema_db) -> None:
    """Signal rows cannot outlive their edge or name an unknown channel."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select pg_get_constraintdef(oid)
            from pg_constraint
            where conrelid = 'post_lineage_edge_signal'::regclass
            order by conname
            """
        )
        definitions = " ".join(row[0].casefold() for row in cur.fetchall())
        assert "references post_lineage_edge" in definitions
        assert "on delete cascade" in definitions
        assert "references common_lookup_value" in definitions
        cur.execute(
            "select lookup_code from common_lookup_value "
            "where lookup_category = 'lineage_signal' order by display_order"
        )
        assert [row[0] for row in cur.fetchall()] == [
            "lineage_signal_temporal",
            "lineage_signal_secondary_key",
            "lineage_signal_text",
            "lineage_signal_llm",
        ]
        cur.execute(
            """
            select data_type, numeric_precision, numeric_scale
            from information_schema.columns
            where table_name = 'post_lineage_edge_signal'
              and column_name in ('signal_score', 'signal_weight', 'signal_contribution')
            """
        )
        for data_type, precision, scale in cur.fetchall():
            assert data_type == "numeric"
            assert precision == 8
            assert scale == 6
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_name in (
                'post_lineage_edge_signal',
                'event_lineage_rebuild',
                'event_lineage_rebuild_channel'
            ) and data_type = 'jsonb'
            """
        )
        assert cur.fetchall() == []


def test_lineage_signal_tables_reject_other_lookup_categories(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
            "values ('test_category', 'not_lineage_signal', 'Not lineage')"
        )
        cur.execute(
            "insert into event_lineage_rebuild "
            "(rebuild_lock, reconstruction_version, generated_at, min_fused_score, candidate_window) "
            "values (true, 'test', now(), 0.3, 50)"
        )
        statements = (
            "insert into event_lineage_rebuild_channel "
            "(rebuild_lock, signal_code, signal_weight) "
            "values (true, 'not_lineage_signal', 0.5)",
            "insert into post_lineage_edge_signal "
            "(parent_post_id, child_post_id, signal_code, signal_score, signal_weight, signal_contribution) "
            "values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', "
            "'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'not_lineage_signal', 0.5, 0.5, 0.25)",
        )
        for index, statement in enumerate(statements):
            savepoint = f"wrong_signal_{index}"
            cur.execute(f"savepoint {savepoint}")
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(statement)
            cur.execute(f"rollback to savepoint {savepoint}")
    schema_db.rollback()


def test_lineage_channel_evidence_migration_upgrades_existing_tables(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            "alter table event_lineage_rebuild_channel "
            "drop constraint event_lineage_rebuild_channel_signal_code_check"
        )
        cur.execute(
            "alter table post_lineage_edge_signal "
            "drop constraint post_lineage_edge_signal_code_check"
        )
        cur.execute(_CHANNEL_EVIDENCE_MIGRATION.read_text())
        cur.execute(
            "select conname from pg_constraint where conname in ("
            "'event_lineage_rebuild_channel_signal_code_check', "
            "'post_lineage_edge_signal_code_check') order by conname"
        )
        assert [row[0] for row in cur.fetchall()] == [
            "event_lineage_rebuild_channel_signal_code_check",
            "post_lineage_edge_signal_code_check",
        ]
    schema_db.commit()


def test_leftover_pair_names_nullable_observed_and_expected_columns(schema_db) -> None:
    """Every install path preserves legacy pairs while naming new Y and E."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select column_name, is_nullable
            from information_schema.columns
            where table_name = 'report_leftover_pair'
            """
        )
        columns = dict(cur.fetchall())
        cur.execute(
            """
            select count(*)
            from pg_constraint
            where conname = 'leftover_pair_observed_expected_reconcile_chk'
            """
        )
        reconcile_constraint_count = cur.fetchone()[0]
    assert columns["observed_response"] == "YES"
    assert columns["expected_response"] == "YES"
    assert columns["leftover_residual"] == "NO"
    assert reconcile_constraint_count == 1


def test_leftover_pair_names_leftover_map_rank_column(schema_db) -> None:
    """Fresh leftover rows name map rank without backfilling legacy evidence."""
    with schema_db.cursor() as cur:
        cur.execute(
            "select column_name, is_nullable from information_schema.columns "
            "where table_name = 'report_leftover_pair'"
        )
        columns = dict(cur.fetchall())
    assert columns["leftover_map_rank"] == "YES"


def test_leftover_pair_names_nullable_unexplained_column(schema_db) -> None:
    """Every install path preserves legacy pairs while naming unexplained leftover."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select column_name, is_nullable
            from information_schema.columns
            where table_name = 'report_leftover_pair'
            """
        )
        columns = dict(cur.fetchall())
    assert columns["leftover_map_unexplained"] == "YES"
    assert columns["leftover_residual"] == "NO"
    assert columns["leftover_distance"] == "NO"
    assert columns["leftover_map_reconstruction"] == "YES"


def test_leftover_pair_names_nullable_cross_share_column(schema_db) -> None:
    """Every install path preserves legacy pairs while naming leftover-map cross share."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select column_name, is_nullable
            from information_schema.columns
            where table_name = 'report_leftover_pair'
            """
        )
        columns = dict(cur.fetchall())
    assert columns["leftover_map_cross_share"] == "YES"
    assert columns["leftover_residual"] == "NO"
    assert columns["leftover_distance"] == "NO"
    assert "leftover_map_explained_share" not in columns
    assert "leftover_map_unexplained_share" not in columns
    assert columns["leftover_map_reconstruction"] == "YES"
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select conname
            from pg_constraint
            where conrelid = 'report_leftover_pair'::regclass
              and conname like '%share%chk'
            """
        )
        assert cur.fetchall() == []


def test_leftover_map_axis_references_period_score(schema_db) -> None:
    """Axis share is report-level; it must cascade with the period score."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select confrelid::regclass::text
            from pg_constraint
            where conrelid = 'report_leftover_map_axis'::regclass and contype = 'f'
            """
        )
        targets = {row[0] for row in cur.fetchall()}
    assert "report_period_score" in targets


def test_leftover_map_coverage_references_period_score(schema_db) -> None:
    """Complete-case leftover coverage is 1:1 with the period report."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select confrelid::regclass::text
            from pg_constraint
            where conrelid = 'report_leftover_map_coverage'::regclass and contype = 'f'
            """
        )
        targets = {row[0] for row in cur.fetchall()}
    assert "report_period_score" in targets


def test_corporate_hierarchy_recursive_query_returns_correct_shape(schema_db) -> None:
    """The real product requirement: 'Acme Group -> Acme Electronics Korea
    -> Acme Electronics Gwangju Plant' must be walkable with one query,
    with no fixed limit on how many levels deep the tree goes.
    """
    with schema_db.cursor() as cur:
        cur.execute(
            "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
            "('corporate_entity_level', 'group', 'Group'), "
            "('corporate_entity_level', 'company', 'Company'), "
            "('corporate_entity_level', 'plant', 'Plant')"
        )
        cur.execute(
            "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
            "values ('ACME-GROUP', 'Acme Group', 'group') returning corporate_entity_id",
        )
        group_id = cur.fetchone()[0]
        cur.execute(
            "insert into corporate_entity (parent_entity_id, corporate_entity_code, entity_name, entity_level_code) "
            "values (%s, 'ACME-KOREA', 'Acme Electronics Korea', 'company') returning corporate_entity_id",
            (group_id,),
        )
        company_id = cur.fetchone()[0]
        cur.execute(
            "insert into corporate_entity (parent_entity_id, corporate_entity_code, entity_name, entity_level_code) "
            "values (%s, 'ACME-GWANGJU', 'Acme Electronics Gwangju Plant', 'plant')",
            (company_id,),
        )
        cur.execute(
            """
            with recursive entity_tree as (
                select corporate_entity_id, entity_name, 0 as depth
                from corporate_entity where parent_entity_id is null
                union all
                select c.corporate_entity_id, c.entity_name, t.depth + 1
                from corporate_entity c join entity_tree t on c.parent_entity_id = t.corporate_entity_id
            )
            select entity_name, depth from entity_tree order by depth
            """
        )
        rows = cur.fetchall()

    assert [name for name, _ in rows] == [
        "Acme Group",
        "Acme Electronics Korea",
        "Acme Electronics Gwangju Plant",
    ]
    assert [depth for _, depth in rows] == [0, 1, 2]


def test_invalid_lookup_code_is_rejected_by_a_real_foreign_key(schema_db) -> None:
    """Referential integrity is actually enforced by the database, not
    just documented as an intention the application layer might forget.
    """
    with schema_db.cursor() as cur:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('BAD-ENTITY', 'Bad Entity', 'not_a_real_code')"
            )
    schema_db.rollback()


def test_lookup_code_is_unique_across_categories(schema_db) -> None:
    """The deliberate simplification documented in the migration: a single-
    column FK to common_lookup_value requires lookup_code to be globally
    unique, not just unique within its category.
    """
    with schema_db.cursor() as cur:
        cur.execute(
            "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
            "values ('post_visibility', 'draft', 'Draft')"
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('ticket_status', 'draft', 'Draft')"
            )
    schema_db.rollback()


def test_every_created_table_name_has_at_least_two_words() -> None:
    """Enforce naming for ordinary and idempotent table declarations."""
    import re

    sql = _MIGRATION_PATH.read_text()
    names = re.findall(
        r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z][a-z0-9_]*)",
        sql,
        flags=re.IGNORECASE,
    )
    assert names, "migration must create at least one table"
    for name in names:
        words = name.split("_")
        assert len(words) >= 2, f"table {name!r} must be two or more snake_case words"


def test_cataloged_team_null_affiliation_is_unique(schema_db) -> None:
    """Repeated NULL-affiliation upserts return one catalog identity."""
    with schema_db.cursor() as cursor:
        ids = []
        for _ in range(2):
            cursor.execute(
                "insert into cataloged_team (team_name, affiliated_organization_name) "
                "values ('Synthetic Design Team', null) "
                "on conflict (team_name, affiliated_organization_name) do update "
                "set team_name = excluded.team_name returning team_id"
            )
            ids.append(cursor.fetchone()[0])
        cursor.execute(
            "select count(*) from cataloged_team "
            "where team_name = 'Synthetic Design Team' "
            "and affiliated_organization_name is null"
        )
        count = cursor.fetchone()[0]
    assert ids[0] == ids[1]
    assert count == 1

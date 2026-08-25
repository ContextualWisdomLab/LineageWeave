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

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "0001_initial_schema.sql"
)
_MAJOR_EVENT_ACTION_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0100_major_event_action.sql"
)
_PROJECT_MENTION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0031_semantic_project_mentions.sql"
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
_CHANNEL_EVIDENCE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0174_post_lineage_edge_signal.sql"
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
_OPERATIONS_CASE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0208_operations_case_analysis.sql"
)
_OPERATIONS_CASE_EVIDENCE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0209_operations_case_evidence_source.sql"
)
_OPERATIONS_CASE_MISSING_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0211_operations_case_missing_fact.sql"
)
_OPERATIONS_CASE_MILESTONE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0215_operations_case_milestone.sql"
)
_ANALYSIS_RUN_REGISTRY_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0018_analysis_run_registry.sql"
)
_TOPIC_CONTEXT_INFLUENCE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0214_topic_context_influence_projection.sql"
)
_TOPIC_LINEAGE_KIND_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0131_analysis_run_topic_lineage_kind.sql"
)
_OPERATIONS_EXTERNAL_RELATION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0213_operations_external_relation_target.sql"
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
        try:
            with conn.cursor() as cur:
                cur.execute(_MIGRATION_PATH.read_text())
                cur.execute(_ANALYSIS_RUN_REGISTRY_MIGRATION.read_text())
                cur.execute(_TOPIC_LINEAGE_KIND_MIGRATION.read_text())
                cur.execute(_PROJECT_MENTION_MIGRATION.read_text())
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
                cur.execute(_OPERATIONS_CASE_MIGRATION.read_text())
                cur.execute(_OPERATIONS_CASE_EVIDENCE_MIGRATION.read_text())
                cur.execute(_OPERATIONS_CASE_MISSING_MIGRATION.read_text())
                cur.execute(_TOPIC_CONTEXT_INFLUENCE_MIGRATION.read_text())
                cur.execute(_OPERATIONS_EXTERNAL_RELATION_MIGRATION.read_text())
            conn.commit()
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
        "operations_case_analysis",
        "operations_case_classification",
        "operations_case_fact",
        "operations_case_missing_fact",
        "topic_model_run",
        "topic_definition",
        "topic_activity_interval",
        "topic_lineage_relation",
        "topic_context_definition",
        "topic_context_membership",
        "topic_influence_run",
        "topic_post_context_influence",
    }
    assert expected <= tables


def test_topic_influence_schema_binds_exact_producer_provenance(schema_db) -> None:
    """Accepted influence runs cannot cross a TEPP run, snapshot, or cutoff."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select tgname
              from pg_trigger
             where tgname = 'topic_influence_run_binding_check'
               and not tgisinternal
            """
        )
        assert cur.fetchone() == ("topic_influence_run_binding_check",)
        cur.execute(
            """
            select tgname
              from pg_trigger
             where tgname = 'topic_model_run_binding_check'
               and not tgisinternal
            """
        )
        assert cur.fetchone() == ("topic_model_run_binding_check",)
        cur.execute(
            """
            select conname
              from pg_constraint
             where conrelid = 'topic_post_context_influence'::regclass
               and contype = 'f'
            """
        )
        foreign_keys = {row[0] for row in cur.fetchall()}
    assert len(foreign_keys) == 3

    account_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    run_id = uuid.uuid4()
    with schema_db.cursor() as cur:
        cur.execute(
            "insert into user_account (user_account_id, external_subject_id, display_name, email_address) values (%s, %s, %s, %s)",
            (str(account_id), f"synthetic-{account_id}", "Synthetic Reviewer", f"synthetic-{account_id}@example.invalid"),
        )
        cur.execute(
            """
            insert into analysis_source_snapshot
                (analysis_source_snapshot_id, snapshot_sha256, source_contract_version,
                 maximum_available_time, captured_at, created_at)
            values (%s, %s, 'synthetic-v1', '2026-08-01T00:00:00Z',
                    '2026-08-02T00:00:00Z', '2026-08-03T00:00:00Z')
            """,
            (str(snapshot_id), "a" * 64),
        )
        cur.execute(
            """
            insert into analysis_run
                (analysis_run_id, analysis_source_snapshot_id, run_kind_code,
                 requested_by_account_id, idempotency_key, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, %s, 'analysis_run_topic_lineage', %s, 'synthetic-topic-run',
                    '2026-08-01T00:00:00Z', 'synthetic-v1', %s, %s,
                    '2026-08-04T00:00:00Z')
            """,
            (str(run_id), str(snapshot_id), str(account_id), "b" * 64, "c" * 40),
        )
        cur.execute("savepoint topic_model_mismatch")
        with pytest.raises(psycopg2.errors.RaiseException, match="topic_model_run_provenance_binding_mismatch"):
            cur.execute(
                """
                insert into topic_model_run
                    (analysis_run_id, tepp_run_id, tepp_snapshot_id,
                     tepp_schema_version, tepp_model_contract_version,
                     tepp_artifact_sha256, reported_source_snapshot_sha256,
                     reported_knowledge_cutoff, posterior_draw_set_id,
                     posterior_draw_count, topic_count, inference_status_code)
                values (%s, 'tepp-mismatch', 'snapshot-mismatch',
                        'tepp.topic_context_posterior.v1', 'trsl-tm-v1', %s, %s,
                        '2026-08-01T00:00:00Z', 'draws-1', 8, 2,
                        'posterior_topic_coordinates_not_importance')
                """,
                (str(run_id), "d" * 64, "e" * 64),
            )
        cur.execute("rollback to savepoint topic_model_mismatch")
        cur.execute(
            """
            insert into topic_model_run
                (analysis_run_id, tepp_run_id, tepp_snapshot_id,
                 tepp_schema_version, tepp_model_contract_version,
                 tepp_artifact_sha256, reported_source_snapshot_sha256,
                 reported_knowledge_cutoff, posterior_draw_set_id,
                 posterior_draw_count, topic_count, inference_status_code)
            values (%s, 'tepp-accepted', 'snapshot-accepted',
                    'tepp.topic_context_posterior.v1', 'trsl-tm-v1', %s, %s,
                    '2026-08-01T00:00:00Z', 'draws-1', 8, 2,
                    'posterior_topic_coordinates_not_importance')
            returning topic_model_run_id
            """,
            (str(run_id), "d" * 64, "a" * 64),
        )
        model_id = cur.fetchone()[0]
        cur.execute("savepoint topic_influence_mismatch")
        with pytest.raises(psycopg2.errors.RaiseException, match="topic_influence_provenance_binding_mismatch"):
            cur.execute(
                """
                insert into topic_influence_run
                    (topic_model_run_id, fast_mlsirm_schema_version,
                     fast_mlsirm_version, fast_mlsirm_code_revision,
                     fast_mlsirm_artifact_sha256, reported_tepp_run_id,
                     reported_snapshot_sha256, reported_knowledge_cutoff,
                     membership_fingerprint_sha256, compute_backend_code,
                     precision_code, posterior_draw_coverage,
                     convergence_status_code, identification_status_code,
                     parity_status_code)
                values (%s, 'fast_mlsirm.topic_context_influence.v1', '0.1.0',
                        %s, %s, 'different-tepp-run', %s,
                        '2026-08-01T00:00:00Z', %s, 'rust_cpu', 'f64', 8,
                        'converged', 'identified', 'passed')
                """,
                (model_id, "f" * 40, "1" * 64, "a" * 64, "2" * 64),
            )
        cur.execute("rollback to savepoint topic_influence_mismatch")


def test_topic_influence_projection_migration_replays(schema_db) -> None:
    """The additive topic projection remains safe under sorted startup replay."""
    with schema_db.cursor() as cur:
        cur.execute(_TOPIC_CONTEXT_INFLUENCE_MIGRATION.read_text())
    schema_db.commit()


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

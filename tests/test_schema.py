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
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import psycopg2
import psycopg2.errors
import pytest

from backend.app.post_content_queue import RUNNING
from backend.app.post_content_worker import _lock_current_claim

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
_BOOKMARK_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0043_bookmark.sql"
)
_IDENTIFIER_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0104_two_word_database_identifiers.sql"
)
_AFFILIATION_SCOPE_FACET_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0106_account_affiliation_scope_facet.sql"
)
_ROLE_AFFILIATION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0107_role_affiliation_catalog_identity.sql"
)
_QUANTITATIVE_OBSERVATION_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0108_post_summary_quantitative_observation.sql"
)
_SOURCE_FACT_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0109_post_summary_source_fact.sql"
)
_SOFTWARE_AGENT_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0110_role_responsibility_software_agent.sql"
)
_SEMANTIC_RELATIONSHIP_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0111_post_summary_semantic_relationship.sql"
)
_EVENT_CLUE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0112_event_clue_semantic_projection.sql"
)
_BROAD_FACT_TYPES_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0113_broad_source_fact_types.sql"
)
_SEMANTIC_RELATIONSHIP_PREDICATES_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0114_semantic_relationship_standard_predicates.sql"
)
_PLANNED_FACILITY_RELATIONSHIP_PREDICATE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0138_planned_facility_relation_predicate.sql"
)
_TECHNOLOGY_BENEFIT_RELATION_PREDICATES_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0177_technology_benefit_relation_predicates.sql"
)
_SUMMARY_INPUT_BINDING_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0139_post_summary_input_binding.sql"
)
_POST_CONTENT_QUEUE_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0050_post_content_ingestion_queue.sql"
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
                cur.execute(_PROJECT_MENTION_MIGRATION.read_text())
                cur.execute(_MAJOR_EVENT_ACTION_MIGRATION.read_text())
                cur.execute(_PROJECT_BOUND_ACTION_MIGRATION.read_text())
                cur.execute(_PROJECT_BOUND_EVENT_MIGRATION.read_text())
                cur.execute(_BOOKMARK_MIGRATION.read_text())
                identifier_migration = _IDENTIFIER_MIGRATION.read_text()
                cur.execute(identifier_migration)
                cur.execute(identifier_migration)
                affiliation_scope_migration = _AFFILIATION_SCOPE_FACET_MIGRATION.read_text()
                cur.execute(affiliation_scope_migration)
                cur.execute(affiliation_scope_migration)
                role_affiliation_migration = _ROLE_AFFILIATION_MIGRATION.read_text()
                cur.execute(role_affiliation_migration)
                cur.execute(role_affiliation_migration)
                cur.execute(_QUANTITATIVE_OBSERVATION_MIGRATION.read_text())
                cur.execute(_SOURCE_FACT_MIGRATION.read_text())
                cur.execute(_SOFTWARE_AGENT_MIGRATION.read_text())
                cur.execute(_SEMANTIC_RELATIONSHIP_MIGRATION.read_text())
                cur.execute(_EVENT_CLUE_MIGRATION.read_text())
                cur.execute(_BROAD_FACT_TYPES_MIGRATION.read_text())
                cur.execute(_SEMANTIC_RELATIONSHIP_PREDICATES_MIGRATION.read_text())
                planned_predicate_migration = (
                    _PLANNED_FACILITY_RELATIONSHIP_PREDICATE_MIGRATION.read_text()
                )
                cur.execute(planned_predicate_migration)
                cur.execute(planned_predicate_migration)
                technology_benefit_migration = (
                    _TECHNOLOGY_BENEFIT_RELATION_PREDICATES_MIGRATION.read_text()
                )
                cur.execute(technology_benefit_migration)
                cur.execute(technology_benefit_migration)
                summary_input_migration = _SUMMARY_INPUT_BINDING_MIGRATION.read_text()
                cur.execute(summary_input_migration)
                cur.execute(summary_input_migration)
                cur.execute(_POST_CONTENT_QUEUE_MIGRATION.read_text())
                cur.execute(_LEFTOVER_OBSERVED_EXPECTED_MIGRATION.read_text())
                cur.execute(_LEFTOVER_MAP_RANK_MIGRATION.read_text())
            conn.commit()
            yield conn
        finally:
            conn.close()
    finally:
        with admin_conn.cursor() as cur:
            cur.execute(f'drop database "{db_name}"')
        admin_conn.close()


def test_post_content_claim_lock_order_avoids_source_job_deadlock(schema_db) -> None:
    """A source holder can lock the job while a worker waits on that source."""
    post_id = uuid.uuid4()
    body = "A synthetic body for the lock-order regression."
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    with schema_db.cursor() as cur:
        cur.execute(
            """
            insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
            values
                ('corporate_entity_level', 'company', 'Company'),
                ('voc_type', 'voc', 'Voice of Customer'),
                ('post_visibility', 'public', 'Public')
            """
        )
        cur.execute(
            """
            with synthetic_entity as (
                insert into corporate_entity (
                    corporate_entity_code, entity_name, entity_level_code
                ) values ('SYNTHETIC-LOCK-ORG', 'Synthetic Lock Org', 'company')
                returning corporate_entity_id
            ), synthetic_account as (
                insert into user_account (
                    external_subject_id, display_name, email_address
                ) values (
                    'synthetic-lock-account', 'Synthetic Lock User',
                    'synthetic.lock@example.test'
                ) returning user_account_id
            )
            insert into source_post (
                post_id, author_account_id, corporate_entity_id,
                post_title, post_body, voc_type_code, visibility_code
            )
            select %s, user_account_id, corporate_entity_id,
                   'Synthetic lock post', %s, 'voc', 'public'
              from synthetic_account cross join synthetic_entity
            """,
            (str(post_id), body),
        )
        cur.execute(
            """
            insert into post_content_ingestion_job (
                post_id, source_body_sha256, status_code, attempt_count, started_at
            ) values (%s, %s, %s, 1, now())
            """,
            (str(post_id), digest, RUNNING),
        )
    schema_db.commit()

    async def exercise() -> None:
        parsed_admin_dsn = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(
            parsed_admin_dsn._replace(path=f"/{schema_db.info.dbname}")
        )
        first = await asyncpg.connect(database_dsn)
        worker = await asyncpg.connect(database_dsn)
        observer = await asyncpg.connect(database_dsn)
        first_tx = first.transaction()
        await first_tx.start()
        worker_task: asyncio.Task[bool] | None = None
        try:
            await first.fetchrow(
                "select post_body from source_post where post_id = $1 for update",
                post_id,
            )

            async def lock_worker_claim() -> bool:
                async with worker.transaction():
                    return await _lock_current_claim(
                        worker,
                        str(post_id),
                        expected_source_body_sha256=digest,
                        expected_attempt_count=1,
                    )

            worker_task = asyncio.create_task(lock_worker_claim())
            for _attempt in range(100):
                waiting = await observer.fetchval(
                    "select wait_event_type = 'Lock' from pg_stat_activity where pid = $1",
                    worker.get_server_pid(),
                )
                if waiting:
                    break
                await asyncio.sleep(0.01)
            else:
                raise AssertionError("worker did not reach the source-row lock")

            await asyncio.wait_for(
                first.fetchrow(
                    "select status_code from post_content_ingestion_job "
                    "where post_id = $1 for update",
                    post_id,
                ),
                timeout=1,
            )
            await first_tx.commit()
            assert await asyncio.wait_for(worker_task, timeout=1) is True
        finally:
            if first.is_in_transaction():
                await first_tx.rollback()
            if worker_task is not None and not worker_task.done():
                worker_task.cancel()
            await first.close()
            await worker.close()
            await observer.close()

    asyncio.run(exercise())


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
        "post_evaluation_response",
        "report_period_score",
        "report_member_score",
        "report_item_parameter",
        "report_item_information",
        "report_leftover_pair",
        "post_summary_result",
        "post_summary_event",
        "post_summary_event_clue",
        "post_summary_role",
        "post_summary_action",
        "post_chat_result",
        "post_chat_citation",
        "post_bookmark",
        "post_summary_quantitative_observation",
        "post_summary_source_fact",
        "post_summary_semantic_relationship",
    }
    assert expected <= tables


def test_summary_result_accepts_only_normalized_sha256_binding(schema_db) -> None:
    with schema_db.cursor() as cur:
        cur.execute(
            "select is_nullable from information_schema.columns "
            "where table_name = 'post_summary_result' "
            "and column_name = 'summary_input_sha256'"
        )
        assert cur.fetchone() == ("YES",)
        cur.execute(
            "select pg_get_constraintdef(oid) from pg_constraint "
            "where conname = 'post_summary_result_summary_input_sha256_check'"
        )
        assert "[0-9a-f]{64}" in cur.fetchone()[0]


def test_planned_facility_relationship_predicate_persists(schema_db) -> None:
    """Migration 0138 must admit the source-backed ADR 0142 relationship."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            insert into common_lookup_value (
                lookup_category, lookup_code, lookup_label
            ) values
                ('corporate_entity_level', 'company', 'Company'),
                ('voc_type', 'voc', 'Voice of Customer'),
                ('post_visibility', 'public', 'Public')
            """
        )
        cur.execute(
            """
            with synthetic_entity as (
                insert into corporate_entity (
                    corporate_entity_code, entity_name, entity_level_code
                ) values ('SYNTHETIC-PLAN-ORG', 'Synthetic Planning Org', 'company')
                returning corporate_entity_id
            ), synthetic_account as (
                insert into user_account (
                    external_subject_id, display_name, email_address
                ) values (
                    'synthetic-plan-account', 'Synthetic Planner',
                    'synthetic.planner@example.test'
                ) returning user_account_id
            ), synthetic_post as (
                insert into source_post (
                    author_account_id, corporate_entity_id, post_title, post_body,
                    voc_type_code, visibility_code
                )
                select user_account_id, corporate_entity_id,
                       'Synthetic facility plan',
                       'Synthetic Planning Org plans to operate Aurora Charging Hub',
                       'voc', 'public'
                  from synthetic_account cross join synthetic_entity
                returning post_id
            ), synthetic_summary as (
                insert into post_summary_result (post_id, korean_summary)
                select post_id, '합성 계획 요약입니다.' from synthetic_post
                returning post_id
            )
            insert into post_summary_semantic_relationship (
                post_id, relation_ordinal, subject_name, subject_type,
                predicate_code, object_name, object_type, evidence_text,
                relation_confidence
            )
            select post_id, 0, 'Synthetic Planning Org', 'organization',
                   'lw_plans_to_operate', 'Aurora Charging Hub',
                   'industrial_asset',
                   'Synthetic Planning Org plans to operate Aurora Charging Hub',
                   0.93
              from synthetic_summary
            returning predicate_code
            """
        )
        assert cur.fetchone() == ("lw_plans_to_operate",)


def test_technology_benefit_relationship_predicates_persist(schema_db) -> None:
    """Migration 0177 must admit the ADR 0146 technology-transfer rows."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            insert into common_lookup_value (
                lookup_category, lookup_code, lookup_label
            ) values
                ('corporate_entity_level', 'company', 'Company'),
                ('voc_type', 'voc', 'Voice of Customer'),
                ('post_visibility', 'public', 'Public')
            """
        )
        cur.execute(
            """
            with synthetic_entity as (
                insert into corporate_entity (
                    corporate_entity_code, entity_name, entity_level_code
                ) values ('SYNTHETIC-TECH-ORG', 'Synthetic Adopter Org', 'company')
                returning corporate_entity_id
            ), synthetic_account as (
                insert into user_account (
                    external_subject_id, display_name, email_address
                ) values (
                    'synthetic-tech-account', 'Synthetic Author',
                    'synthetic.author@example.test'
                ) returning user_account_id
            ), synthetic_post as (
                insert into source_post (
                    author_account_id, corporate_entity_id, post_title, post_body,
                    voc_type_code, visibility_code
                )
                select user_account_id, corporate_entity_id,
                       'Synthetic technology adoption',
                       'Synthetic Adopter Org adopted the diagnostics model from Synthetic Provider Org',
                       'voc', 'public'
                  from synthetic_account cross join synthetic_entity
                returning post_id
            ), synthetic_summary as (
                insert into post_summary_result (post_id, korean_summary)
                select post_id, '합성 기술 도입 요약입니다.' from synthetic_post
                returning post_id
            )
            insert into post_summary_semantic_relationship (
                post_id, relation_ordinal, subject_name, subject_type,
                predicate_code, object_name, object_type, evidence_text,
                relation_confidence
            )
            select post_id, ordinal, 'Diagnostics Model', 'technology',
                   predicate_code, object_name, object_type,
                   'Synthetic Adopter Org adopted the diagnostics model from Synthetic Provider Org',
                   0.9
              from synthetic_summary
             cross join (values
                (0, 'lw_technology_provided_by', 'Synthetic Provider Org', 'organization'),
                (1, 'lw_technology_adopted_by', 'Synthetic Adopter Org', 'organization'),
                (2, 'lw_technology_applied_to', 'Highland HVDC', 'project')
             ) as rows(ordinal, predicate_code, object_name, object_type)
            returning predicate_code
            """
        )
        assert {row[0] for row in cur.fetchall()} == {
            "lw_technology_provided_by",
            "lw_technology_adopted_by",
            "lw_technology_applied_to",
        }


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


def test_affiliation_scope_facet_defaults_to_unclassified_and_rejects_bad_codes(schema_db) -> None:
    """ADR 0125 step 1: an account_affiliation row that doesn't specify a
    scope facet lands on the honest 'unclassified' state, not a silently
    guessed own/customer label, and the column is a real foreign key.
    """
    with schema_db.cursor() as cur:
        cur.execute(
            "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
            "values ('corporate_entity_level', 'company', 'Company') on conflict do nothing"
        )
        cur.execute(
            "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
            "values ('CASE-ENTITY', 'Case Entity', 'company') returning corporate_entity_id"
        )
        entity_id = cur.fetchone()[0]
        cur.execute(
            "insert into user_account (external_subject_id, display_name, email_address) "
            "values ('case-subject', 'Case User', 'case@example.test') returning user_account_id"
        )
        account_id = cur.fetchone()[0]
        cur.execute(
            "insert into account_affiliation (user_account_id, corporate_entity_id) "
            "values (%s, %s) returning affiliation_scope_code",
            (account_id, entity_id),
        )
        assert cur.fetchone()[0] == "scope_unclassified"

        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "insert into account_affiliation (user_account_id, corporate_entity_id, affiliation_scope_code) "
                "values (%s, %s, 'not_a_real_scope')",
                (account_id, entity_id),
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


def test_identifier_migration_leaves_no_single_word_public_identifiers(schema_db) -> None:
    """The current schema contract covers tables, views, and their columns."""
    with schema_db.cursor() as cur:
        cur.execute(
            """
            select table_name
              from information_schema.tables
             where table_schema = 'public'
               and table_type = 'BASE TABLE'
               and table_name !~ '^[a-z][a-z0-9]*(_[a-z0-9]+)+$'
            """
        )
        invalid_tables = {row[0] for row in cur.fetchall()}
        cur.execute(
            """
            select table_name, column_name
              from information_schema.columns
             where table_schema = 'public'
               and column_name !~ '^[a-z][a-z0-9]*(_[a-z0-9]+)+$'
            """
        )
        invalid_columns = {(row[0], row[1]) for row in cur.fetchall()}
    assert invalid_tables == set()
    assert invalid_columns == set()


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

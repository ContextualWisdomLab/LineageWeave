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

import psycopg2
import psycopg2.errors
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "0001_initial_schema.sql"


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
        db_dsn = _ADMIN_DSN.rsplit("/", 1)[0] + f"/{db_name}"
        conn = psycopg2.connect(db_dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(_MIGRATION_PATH.read_text())
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
        "cataloged_person",
        "person_affiliation",
        "post_person_mention",
        "knowledge_graph_edge",
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
        "post_summary_role",
        "post_chat_result",
        "post_chat_citation",
    }
    assert expected <= tables


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
    """The project naming rule is enforced on the shipped migration, not
    only on tables that happen to be created in a live-Postgres run.
    """
    import re

    sql = _MIGRATION_PATH.read_text()
    names = re.findall(r"create table (\w+)", sql)
    assert names, "migration must create at least one table"
    for name in names:
        words = name.split("_")
        assert len(words) >= 2, f"table {name!r} must be two or more snake_case words"

"""Real-PostgreSQL proof that hidden records cannot influence project history."""

from __future__ import annotations

import asyncio
from datetime import datetime
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import uuid

import asyncpg
import psycopg2
from psycopg2 import sql
import pytest

from backend.app.project_history_api import ProjectHistoryProjection
from backend.app.project_history import fetch_project_history_projection


_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS = tuple(
    _ROOT / "migrations" / name
    for name in (
        "0001_initial_schema.sql",
        "0031_semantic_project_mentions.sql",
        "0033_source_state_provenance.sql",
        "0034_source_context_provenance.sql",
        "0038_source_named_hints.sql",
        "0039_source_org_named_hints.sql",
        "0053_project_history_lookup.sql",
    )
)


def _postgres_available() -> bool:
    """Return whether the configured PostgreSQL service accepts connections."""

    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


def _database_dsn(database_name: str) -> str:
    """Replace the DSN database path while preserving connection options."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def project_history_database() -> tuple[str, str]:
    """Create a migrated database with visible, hidden, and excluded evidence."""

    database_name = f"lineageweave_project_history_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    database_dsn = _database_dsn(database_name)
    connection = psycopg2.connect(database_dsn)
    try:
        with connection.cursor() as cursor:
            for migration in _MIGRATIONS:
                cursor.execute(migration.read_text(encoding="utf-8"))
            cursor.execute(
                """
                insert into common_lookup_value
                    (lookup_category, lookup_code, lookup_label)
                values
                    ('corporate_entity_level', 'company', 'Company'),
                    ('post_visibility', 'public', 'Public'),
                    ('post_visibility', 'private', 'Private'),
                    ('voc_type', 'voc', 'Voice of Customer'),
                    ('voc_type', 'vom', 'Voice of Market'),
                    ('person_side', 'our_side', 'Our side'),
                    ('prov_agent_type', 'prov_person', 'Person'),
                    ('prov_agent_type', 'prov_organization', 'Organization'),
                    ('prov_agent_type', 'prov_team', 'Team')
                on conflict (lookup_code) do nothing
                """
            )
            cursor.execute(
                """
                insert into corporate_entity
                    (corporate_entity_code, entity_name, entity_level_code)
                values ('OWN-CORP', 'Own Corp', 'company')
                returning corporate_entity_id
                """
            )
            own_corporate_entity_id = cursor.fetchone()[0]
            cursor.execute(
                """
                insert into corporate_entity
                    (corporate_entity_code, entity_name, entity_level_code)
                values ('OTHER-CORP', 'Other Corp', 'company')
                returning corporate_entity_id
                """
            )
            other_corporate_entity_id = cursor.fetchone()[0]
            cursor.execute(
                """
                insert into user_account
                    (external_subject_id, display_name, email_address)
                values ('history-user', 'History User', 'history@example.test')
                returning user_account_id
                """
            )
            account_id = cursor.fetchone()[0]

            post_ids: dict[str, str] = {}
            rows = (
                (
                    "award",
                    own_corporate_entity_id,
                    "public",
                    "Contract awarded",
                    "vom",
                    "P-100",
                    None,
                    None,
                    "2026-01-01T09:00:00Z",
                ),
                (
                    "spec",
                    own_corporate_entity_id,
                    "private",
                    "Specification revision requested",
                    "vom",
                    "P-100",
                    None,
                    None,
                    "2026-01-02T09:00:00Z",
                ),
                (
                    "delivery",
                    own_corporate_entity_id,
                    "public",
                    "Delivery confirmed",
                    "vom",
                    None,
                    None,
                    None,
                    "2026-01-03T09:00:00Z",
                ),
                (
                    "voc",
                    own_corporate_entity_id,
                    "public",
                    "VOC received",
                    "voc",
                    "P-100",
                    None,
                    None,
                    "2026-01-04T09:00:00Z",
                ),
                (
                    "hidden",
                    other_corporate_entity_id,
                    "private",
                    "Hidden handoff",
                    "vom",
                    "P-100",
                    None,
                    None,
                    "2026-01-03T12:00:00Z",
                ),
                (
                    "draft",
                    own_corporate_entity_id,
                    "public",
                    "Draft rebid",
                    "vom",
                    "P-100",
                    "draft",
                    None,
                    "2026-01-05T09:00:00Z",
                ),
                (
                    "deleted",
                    own_corporate_entity_id,
                    "public",
                    "Deleted rebid",
                    "vom",
                    "P-100",
                    None,
                    "deleted",
                    "2026-01-05T10:00:00Z",
                ),
                (
                    "future",
                    own_corporate_entity_id,
                    "public",
                    "Future rebid",
                    "vom",
                    "P-100",
                    None,
                    None,
                    "2026-02-01T09:00:00Z",
                ),
            )
            for (
                key,
                corporate_id,
                visibility,
                title,
                voc,
                project_code,
                draft,
                deleted,
                created_at,
            ) in rows:
                cursor.execute(
                    """
                    insert into source_post
                        (author_account_id, corporate_entity_id, post_title, post_body,
                         voc_type_code, visibility_code, source_project_code,
                         source_project_name, source_draft_code, source_deleted_flag,
                         created_at, updated_at)
                    values (%s, %s, %s, 'Synthetic project evidence', %s, %s,
                            %s, 'Northridge renewal', %s, %s, %s, %s)
                    returning post_id
                    """,
                    (
                        account_id,
                        corporate_id,
                        title,
                        voc,
                        visibility,
                        project_code,
                        draft,
                        deleted,
                        created_at,
                        created_at,
                    ),
                )
                post_ids[key] = str(cursor.fetchone()[0])

            cursor.execute(
                """
                insert into post_project_mention
                    (post_id, project_key, project_name, evidence_text,
                     confidence, ontology_iri, extraction_method)
                values
                    (%s, 'Ｐ－１００', 'Northridge renewal',
                     'The delivered project was identified semantically.', 0.910,
                     'https://w3id.org/lineageweave#Project',
                     'contextual_orchestrator_semantic'),
                    (%s, 'P-100', 'Northridge renewal',
                     'The awarded project also has semantic evidence.', 0.990,
                     'https://w3id.org/lineageweave#Project',
                     'contextual_orchestrator_semantic')
                """,
                (post_ids["delivery"], post_ids["award"]),
            )

            people: dict[str, str] = {}
            for name in ("Ada", "Priya", "Hidden Person"):
                cursor.execute(
                    """
                    insert into cataloged_person (person_name, person_side_code)
                    values (%s, 'our_side') returning person_id
                    """,
                    (name,),
                )
                people[name] = str(cursor.fetchone()[0])
            for post_key, actor_name in (
                ("award", "Ada"),
                ("spec", "Ada"),
                ("delivery", "Priya"),
                ("hidden", "Hidden Person"),
            ):
                cursor.execute(
                    """
                    insert into post_summary_result (post_id, korean_summary)
                    values (%s, 'Synthetic summary')
                    """,
                    (post_ids[post_key],),
                )
                cursor.execute(
                    """
                    insert into post_summary_role
                        (post_id, actor_name, responsibility, actor_type_code,
                         affiliated_organization_name, cataloged_person_id)
                    values (%s, %s, 'Own the event', 'prov_person', 'Own Corp', %s)
                    """,
                    (post_ids[post_key], actor_name, people[actor_name]),
                )

            for parent, child, score in (
                ("award", "spec", 0.91),
                ("spec", "delivery", 0.82),
                ("delivery", "voc", 0.73),
                ("hidden", "voc", 1.00),
            ):
                cursor.execute(
                    """
                    insert into post_lineage_edge
                        (parent_post_id, child_post_id, fused_score)
                    values (%s, %s, %s)
                    """,
                    (post_ids[parent], post_ids[child], score),
                )
        connection.commit()
    finally:
        connection.close()

    try:
        yield database_dsn, str(own_corporate_entity_id)
    finally:
        with admin.cursor() as cursor:
            cursor.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s",
                (database_name,),
            )
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin.close()


def test_hidden_draft_deleted_and_future_evidence_cannot_change_history(
    project_history_database: tuple[str, str],
) -> None:
    """Exercise production SQL and prove authorization precedes composition."""

    database_dsn, own_corporate_entity_id = project_history_database

    async def run() -> tuple[dict[str, object], str]:
        connection = await asyncpg.connect(database_dsn)
        try:
            focus_post_id = str(
                await connection.fetchval(
                    "select post_id from source_post where post_title = 'VOC received'"
                )
            )
            hidden_post_id = str(
                await connection.fetchval(
                    "select post_id from source_post where post_title = 'Hidden handoff'"
                )
            )
            projection = await fetch_project_history_projection(
                connection,
                project_key="Ｐ－１００",
                focus_post_id=focus_post_id,
                knowledge_cutoff=datetime.fromisoformat("2026-01-31T23:59:59+00:00"),
                corporate_entity_ids=[own_corporate_entity_id],
                limit=16,
            )
            return projection, hidden_post_id
        finally:
            await connection.close()

    projection, hidden_post_id = asyncio.run(run())
    validated = ProjectHistoryProjection.model_validate(projection)
    assert validated.project_name == "Northridge renewal"
    titles = [event["event_title"] for event in projection["events"]]
    assert titles == [
        "Contract awarded",
        "Specification revision requested",
        "Delivery confirmed",
        "VOC received",
    ]
    assert projection["distinct_observed_actor_count"] == 2
    assert [event["responsibility_transition_code"] for event in projection["events"]] == [
        None,
        "continuous",
        "handoff",
        "assignment_gap",
    ]
    assert all("Hidden" not in title for title in titles)
    assert all(
        hidden_post_id not in path["event_ids"]
        for event in projection["events"]
        for path in event["related_prior_paths"]
    )
    assert [
        match["matched_value"] for match in projection["events"][0]["project_matches"]
    ] == ["P-100", "Northridge renewal", "P-100", "Northridge renewal"]

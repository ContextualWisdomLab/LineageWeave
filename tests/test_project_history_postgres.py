"""Real-PostgreSQL contract tests for the project lifecycle read model."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import uuid

import asyncpg
import psycopg2
from psycopg2 import sql
import pytest

from backend.app.project_history import fetch_project_history

_ROOT = Path(__file__).resolve().parents[1]
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)


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


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def project_history_database() -> str:
    """Create a freshly migrated database with public, scoped, and hidden evidence."""

    database_name = f"lineageweave_project_history_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    try:
        database_dsn = _database_dsn(database_name)
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute((_ROOT / "migrations/0001_initial_schema.sql").read_text())
                cursor.execute((_ROOT / "migrations/0033_source_state_provenance.sql").read_text())
                cursor.execute((_ROOT / "migrations/0034_source_context_provenance.sql").read_text())
                cursor.execute((_ROOT / "migrations/0038_source_named_hints.sql").read_text())
                cursor.execute((_ROOT / "migrations/0039_source_org_named_hints.sql").read_text())
                cursor.execute((_ROOT / "migrations/0050_project_history_lifecycle.sql").read_text())
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
                        ('person_side', 'our_side', 'Our side')
                    on conflict (lookup_code) do nothing
                    """
                )
                cursor.execute(
                    """
                    insert into corporate_entity
                        (corporate_entity_code, entity_name, entity_level_code)
                    values
                        ('PROJECT-CORP-A', 'Project Corp A', 'company'),
                        ('PROJECT-CORP-B', 'Project Corp B', 'company')
                    returning corporate_entity_id, corporate_entity_code
                    """
                )
                entities = {code: entity_id for entity_id, code in cursor.fetchall()}
                cursor.execute(
                    """
                    insert into user_account
                        (external_subject_id, display_name, email_address)
                    values ('project-history-subject', 'Project History User',
                            'project-history@example.test')
                    returning user_account_id
                    """
                )
                account_id = cursor.fetchone()[0]

                def post(
                    title: str,
                    entity_code: str,
                    visibility: str,
                    created_at: str,
                    *,
                    draft: str | None = None,
                ) -> str:
                    cursor.execute(
                        """
                        insert into source_post
                            (author_account_id, corporate_entity_id, post_title,
                             post_body, voc_type_code, visibility_code, created_at,
                             source_draft_code)
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        returning post_id
                        """,
                        (
                            account_id,
                            entities[entity_code],
                            title,
                            f"Evidence for {title}",
                            "voc" if "VOC" in title else "vom",
                            visibility,
                            created_at,
                            draft,
                        ),
                    )
                    return str(cursor.fetchone()[0])

                post_ids = {
                    "order": post(
                        "Order awarded", "PROJECT-CORP-A", "public", "2022-03-14T09:00:00Z"
                    ),
                    "spec": post(
                        "Specification changed", "PROJECT-CORP-A", "private", "2023-06-01T09:00:00Z"
                    ),
                    "delivery_hidden": post(
                        "Delivery hidden", "PROJECT-CORP-B", "private", "2024-11-18T09:00:00Z"
                    ),
                    "draft_hidden": post(
                        "Draft hidden", "PROJECT-CORP-A", "public", "2025-01-01T09:00:00Z", draft="Y"
                    ),
                    "voc": post(
                        "VOC received", "PROJECT-CORP-A", "public", "2026-02-10T09:00:00Z"
                    ),
                }
                cursor.execute(
                    """
                    insert into project_history_project (project_key, project_name)
                    values ('P-1042', 'OO Transformer')
                    """
                )
                event_specs = (
                    ("order", "project_event_order", "Order awarded", "2022-03-14T09:00:00Z"),
                    ("spec", "project_event_spec_change", "Specification changed", "2023-06-01T09:00:00Z"),
                    ("delivery_hidden", "project_event_delivery", "Delivery hidden", "2024-11-18T09:00:00Z"),
                    ("draft_hidden", "project_event_delivery", "Draft hidden", "2025-01-01T09:00:00Z"),
                    ("voc", "project_event_voc", "VOC received", "2026-02-10T09:00:00Z"),
                )
                event_ids: dict[str, str] = {}
                for key, event_type, title, occurred_at in event_specs:
                    cursor.execute(
                        """
                        insert into project_history_event
                            (project_key, event_type_code, event_title,
                             event_start_at, evidence_post_id)
                        values ('P-1042', %s, %s, %s, %s)
                        returning project_history_event_id
                        """,
                        (event_type, title, occurred_at, post_ids[key]),
                    )
                    event_ids[key] = str(cursor.fetchone()[0])

                relation_specs = (
                    ("order", "spec", "project_relation_follows", "spec"),
                    ("spec", "delivery_hidden", "project_relation_follows", "delivery_hidden"),
                    ("delivery_hidden", "voc", "project_relation_related_to", "voc"),
                    ("spec", "voc", "project_relation_related_to", "voc"),
                )
                for source, target, relation_type, evidence in relation_specs:
                    cursor.execute(
                        """
                        insert into project_event_relation
                            (source_project_history_event_id,
                             target_project_history_event_id,
                             relation_type_code, evidence_post_id)
                        values (%s, %s, %s, %s)
                        """,
                        (
                            event_ids[source],
                            event_ids[target],
                            relation_type,
                            post_ids[evidence],
                        ),
                    )

                people: dict[str, str] = {}
                for key, name in (
                    ("sales", "Synthetic Sales Owner"),
                    ("pm", "Synthetic Project Manager"),
                    ("hidden", "Hidden Service Owner"),
                    ("service", "Synthetic Service Owner"),
                ):
                    cursor.execute(
                        """
                        insert into cataloged_person
                            (person_name, person_side_code)
                        values (%s, 'our_side')
                        returning person_id
                        """,
                        (name,),
                    )
                    people[key] = str(cursor.fetchone()[0])

                assignment_specs = (
                    ("sales", "project_role_sales", "2022-03-01T00:00:00Z", "2023-05-20T00:00:00Z", "order"),
                    ("pm", "project_role_project_manager", "2023-06-01T00:00:00Z", "2026-01-01T00:00:00Z", "spec"),
                    ("hidden", "project_role_service", "2025-12-15T00:00:00Z", "2026-02-01T00:00:00Z", "delivery_hidden"),
                    ("service", "project_role_service", "2026-02-10T00:00:00Z", None, "voc"),
                )
                for person_key, role, valid_from, valid_to, evidence in assignment_specs:
                    cursor.execute(
                        """
                        insert into project_responsibility_assignment
                            (project_key, cataloged_person_id,
                             responsibility_role_code, valid_from, valid_to,
                             evidence_post_id)
                        values ('P-1042', %s, %s, %s, %s, %s)
                        """,
                        (people[person_key], role, valid_from, valid_to, post_ids[evidence]),
                    )
            connection.commit()
        finally:
            connection.close()
        yield f"{database_dsn}|{entities['PROJECT-CORP-A']}"
    finally:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin.close()


async def _assert_authorized_projection(database_dsn: str, corporate_entity_id: str) -> None:
    connection = await asyncpg.connect(database_dsn)
    try:
        payload = await fetch_project_history(
            connection,
            "P-1042",
            [corporate_entity_id],
        )
    finally:
        await connection.close()

    assert payload["project_name"] == "OO Transformer"
    assert [event["event_type_code"] for event in payload["events"]] == [
        "project_event_order",
        "project_event_spec_change",
        "project_event_voc",
    ]
    assert {relation["relation_type_code"] for relation in payload["relations"]} == {
        "project_relation_follows",
        "project_relation_related_to",
    }
    assert all(relation["causal"] is False for relation in payload["relations"])
    assert [row["person_name"] for row in payload["responsibility_assignments"]] == [
        "Synthetic Sales Owner",
        "Synthetic Project Manager",
        "Synthetic Service Owner",
    ]
    assert [gap["gap_days"] for gap in payload["handover_gaps"]] == [12.0, 40.0]
    assert all(
        gap["gap_basis"] == "visible_assignment_evidence"
        for gap in payload["handover_gaps"]
    )
    assert payload["evidence_boundary"] == "authorized_source_posts_only"


def test_project_history_filters_hidden_endpoints_and_derived_assignments(
    project_history_database: str,
) -> None:
    database_dsn, corporate_entity_id = project_history_database.split("|", 1)
    asyncio.run(_assert_authorized_projection(database_dsn, corporate_entity_id))

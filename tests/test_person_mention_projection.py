"""Real-PostgreSQL regressions for source-aware person and graph projections.

Keyman extraction and post-summary R&R are independent evidence channels. A
replacement in either channel must remove only that channel's stale person
mentions, then reconcile the buyer-facing Knowledge Graph from the currently
supported union. Orphan graph-registry rows must never become visible.
"""

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

from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.knowledge_graph import (
    hydrate_related_nodes,
    load_visible_subgraph,
    persist_edges_for_post,
    related_for_start,
    visible_mention_post_ids,
)
from backend.app import post_summary_ingestion as summary_ingestion
from backend.app.post_summary_ingestion import (
    fetch_persisted_summary,
    persist_post_summary,
)
from lineageweave.keyman_extraction import OUR_SIDE, PersonMention
from lineageweave.knowledge_graph import (
    EDGE_MENTION,
    EDGE_MENTION_TEAM,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_TEAM,
)
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    KeyEvent,
    MajorEventAction,
    PostSummary,
    ProjectMention,
    RoleResponsibility,
)

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "0001_initial_schema.sql"
_SEMANTIC_PROJECT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0031_semantic_project_mentions.sql"
)
_POST_SUMMARY_CONTRACT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0040_post_summary_contract.sql"
)
_SUMMARY_FIVE_W1H_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0048_post_summary_five_w1h.sql"
)
_MAJOR_EVENT_ACTION_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0100_major_event_action.sql"
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
_SEMANTIC_SEARCH_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0032_semantic_search_trigram.sql"
)
_SOURCE_STATE_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0033_source_state_provenance.sql"
)
_SOURCE_CONTEXT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0034_source_context_provenance.sql"
)
_NORMALIZED_BODY_SEARCH_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0036_normalized_body_search.sql"
)
_SOURCE_RECORD_IDENTITY_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0037_source_record_identity.sql"
)
_SOURCE_NAMED_HINTS_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0038_source_named_hints.sql"
)
_SOURCE_ORG_NAMED_HINTS_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0039_source_org_named_hints.sql"
)
_OPERATIONS_CASE_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0208_operations_case_analysis.sql"
)
_OPERATIONS_EVIDENCE_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0209_operations_case_evidence_source.sql"
)
_OPERATIONS_INPUT_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0222_operations_case_analysis_input.sql"
)
_PRODUCT_SEMANTIC_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0228_product_semantic_catalog.sql"
)


def _postgres_available() -> bool:
    """Return whether the configured real PostgreSQL test service is reachable."""

    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


class _KeymanClient:
    """Mutable deterministic extractor used to model replacement runs."""

    available = True

    def __init__(self, mentions: list[PersonMention]) -> None:
        self.mentions = mentions

    def extract(self, post_title: str, post_body: str) -> list[PersonMention]:
        """Return a copy so production code cannot mutate the fixture."""

        return list(self.mentions)


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN query parameters."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def projection_database() -> str:
    """Create one freshly migrated PostgreSQL database and seed one post."""

    database_name = f"lineageweave_projection_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    try:
        database_dsn = _database_dsn(database_name)
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute(_MIGRATION_PATH.read_text(encoding="utf-8"))
                cursor.execute(_SEMANTIC_PROJECT_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SEMANTIC_SEARCH_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SOURCE_STATE_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SOURCE_CONTEXT_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_NORMALIZED_BODY_SEARCH_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SOURCE_RECORD_IDENTITY_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SOURCE_NAMED_HINTS_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SOURCE_ORG_NAMED_HINTS_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_POST_SUMMARY_CONTRACT_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_SUMMARY_FIVE_W1H_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_MAJOR_EVENT_ACTION_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_PROJECT_BOUND_ACTION_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_PROJECT_BOUND_EVENT_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_OPERATIONS_CASE_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_OPERATIONS_EVIDENCE_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_OPERATIONS_INPUT_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_PRODUCT_SEMANTIC_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(
                    """
                    insert into common_lookup_value
                        (lookup_category, lookup_code, lookup_label)
                    values
                        ('corporate_entity_level', 'company', 'Company'),
                        ('post_visibility', 'public', 'Public'),
                        ('voc_type', 'voc', 'Voice of Customer'),
                        ('person_side', 'our_side', 'Our side'),
                        ('person_side', 'counterparty', 'Counterparty'),
                        ('prov_agent_type', 'prov_person', 'Person'),
                        ('prov_agent_type', 'prov_organization', 'Organization'),
                        ('prov_agent_type', 'prov_team', 'Team'),
                        ('node_type', 'node_person', 'Person node'),
                        ('node_type', 'node_post', 'Post node'),
                        ('node_type', 'node_corporate_entity', 'Corporate node'),
                        ('node_type', 'node_team', 'Team node'),
                        ('edge_type', 'edge_mention', 'Person mentioned in'),
                        ('edge_type', 'edge_affiliation', 'Person affiliated with'),
                        ('edge_type', 'edge_co_mention', 'People co-mentioned'),
                        ('edge_type', 'edge_mention_team', 'Team mentioned in'),
                        ('edge_type', 'edge_team_affiliation', 'Team affiliated with'),
                        ('edge_type', 'edge_mention_organization', 'Organization mentioned in')
                    """
                )
                cursor.execute(
                    """
                    insert into corporate_entity
                        (corporate_entity_code, entity_name, entity_level_code)
                    values ('SYNTH-CORP', 'Synthetic Corp', 'company')
                    returning corporate_entity_id
                    """
                )
                corporate_entity_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    insert into user_account
                        (external_subject_id, display_name, email_address)
                    values ('projection-subject', 'Projection User', 'projection@example.test')
                    returning user_account_id
                    """
                )
                account_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    insert into source_post
                        (author_account_id, corporate_entity_id, post_title, post_body,
                         voc_type_code, visibility_code)
                    values (%s, %s, 'Synthetic post', 'Synthetic body', 'voc', 'public')
                    returning post_id
                    """,
                    (account_id, corporate_entity_id),
                )
                post_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    insert into cataloged_person
                        (person_name, person_side_code, last_known_job_title)
                    values ('Summary Person', 'counterparty', 'Reviewer')
                    returning person_id
                    """
                )
                summary_person_id = cursor.fetchone()[0]
            connection.commit()
        finally:
            connection.close()
        yield "|".join((database_dsn, str(post_id), str(summary_person_id)))
    finally:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin.close()


async def _exercise_projection_contract(
    database_dsn: str,
    post_id: str,
    summary_person_id: str,
) -> None:
    """Run Keyman and R&R replacements and prove graph support follows them."""

    connection = await asyncpg.connect(database_dsn)
    try:
        keyman = PersonMention("Keyman Person", OUR_SIDE)
        client = _KeymanClient([keyman])
        await ingest_post_keymen(
            connection,
            client,
            post_id,
            "Synthetic post",
            "Synthetic body",
        )
        keyman_person_id = str(
            await connection.fetchval(
                "select person_id from cataloged_person where person_name = 'Keyman Person'"
            )
        )

        await persist_post_summary(
            connection,
            post_id,
            PostSummary(
                korean_summary="합성 요약",
                key_event_details=(
                    KeyEvent(event_text="합성 프로젝트 검토", project_key="Synthetic Project"),
                ),
                roles_and_responsibilities=(
                    RoleResponsibility(
                        actor_name="Summary Person",
                        responsibility="검토",
                    ),
                ),
                major_event_actions=(
                    MajorEventAction(
                        action_text="합성 프로젝트 검토 요청",
                        requester_actor_name="Summary Person",
                        processor_actor_name=None,
                        evidence_text="합성 본문에 프로젝트 검토 요청이 기록됨",
                        project_key="Synthetic Project",
                    ),
                    MajorEventAction(
                        action_text="연결되지 않은 프로젝트 요청",
                        requester_actor_name=None,
                        processor_actor_name=None,
                        evidence_text="프로젝트 연결 근거가 없음",
                        project_key="unsupported-project",
                    ),
                ),
                project_mentions=(
                    ProjectMention(
                        project_name="Synthetic Project",
                        canonical_name="Synthetic Project",
                        evidence="합성 본문에 프로젝트명이 있음",
                        confidence=0.9,
                    ),
                ),
            ),
        )
        summary_payload = await fetch_persisted_summary(connection, post_id)
        assert summary_payload is not None
        assert [
            action["project_name"]
            for action in summary_payload["major_event_actions"]
        ] == ["Synthetic Project", None]
        assert summary_payload["key_event_details"] == [
            {"event_text": "합성 프로젝트 검토", "project_name": "Synthetic Project"}
        ]

        keyman_rows = await connection.fetch(
            "select person_id from post_person_mention where post_id = $1",
            post_id,
        )
        summary_rows = await connection.fetch(
            "select person_id from post_summary_person_mention where post_id = $1",
            post_id,
        )
        assert {str(row["person_id"]) for row in keyman_rows} == {keyman_person_id}
        assert {str(row["person_id"]) for row in summary_rows} == {summary_person_id}
        assert await visible_mention_post_ids(
            connection, summary_person_id, lambda row: True
        ) == [post_id]

        await persist_post_summary(
            connection,
            post_id,
            PostSummary(korean_summary="역할이 제거된 합성 요약"),
        )
        assert await visible_mention_post_ids(
            connection, summary_person_id, lambda row: True
        ) == []
        assert await visible_mention_post_ids(
            connection, keyman_person_id, lambda row: True
        ) == [post_id]
        visible_edges = await load_visible_subgraph(connection, [post_id])
        visible_person_ids = {
            edge.source_node_id
            for edge in visible_edges
            if edge.source_node_type_code == NODE_PERSON
        } | {
            edge.target_node_id
            for edge in visible_edges
            if edge.target_node_type_code == NODE_PERSON
        }
        assert summary_person_id not in visible_person_ids
        assert keyman_person_id in visible_person_ids

        client.mentions = []
        await ingest_post_keymen(
            connection,
            client,
            post_id,
            "Synthetic post",
            "Synthetic body",
        )
        assert await visible_mention_post_ids(
            connection, keyman_person_id, lambda row: True
        ) == []
        assert await load_visible_subgraph(connection, [post_id]) == []

        async with connection.transaction():
            await persist_edges_for_post(connection, post_id)
            await persist_edges_for_post(connection, post_id)
        duplicate_count = await connection.fetchval(
            """
            select count(*)
              from (
                    select source_node_type_code, source_node_id,
                           target_node_type_code, target_node_id, edge_type_code
                      from knowledge_graph_edge
                     group by source_node_type_code, source_node_id,
                              target_node_type_code, target_node_id, edge_type_code
                    having count(*) > 1
              ) duplicate_edge
            """
        )
        assert duplicate_count == 0

        orphan_id = await connection.fetchval(
            """
            insert into knowledge_graph_edge
                (source_node_type_code, source_node_id, target_node_type_code,
                 target_node_id, edge_type_code, edge_weight)
            values ($1, $2::uuid, $3, $4::uuid, $5, 1.0)
            on conflict (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id, edge_type_code
            ) do update set edge_weight = excluded.edge_weight
            returning knowledge_graph_edge_id
            """,
            NODE_PERSON,
            keyman_person_id,
            NODE_POST,
            post_id,
            EDGE_MENTION,
        )
        await connection.execute(
            "delete from knowledge_graph_edge_evidence where knowledge_graph_edge_id = $1",
            orphan_id,
        )
        assert await load_visible_subgraph(connection, [post_id]) == []
    finally:
        await connection.close()


def test_person_mention_sources_reconcile_without_stale_graph_edges(
    projection_database: str,
) -> None:
    """Each evidence channel replaces itself and the visible graph follows suit."""

    database_dsn, post_id, summary_person_id = projection_database.split("|")
    asyncio.run(
        _exercise_projection_contract(database_dsn, post_id, summary_person_id)
    )


def test_cross_post_identity_upgrade_keeps_keyman_mention_context(
    projection_database: str,
) -> None:
    """Migration 0016 copies R&R names and must not steal Keyman mention_context."""

    database_dsn, post_id, summary_person_id = projection_database.split("|")
    migration = Path(__file__).resolve().parents[1] / "migrations" / "0016_cross_post_actor_identity.sql"
    connection = psycopg2.connect(database_dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into post_person_mention (post_id, person_id, mention_context)
                values (%s, %s, %s)
                """,
                (
                    post_id,
                    summary_person_id,
                    "Keyman extracted this mention from the synthetic body",
                ),
            )
            cursor.execute(
                "insert into post_summary_result "
                "(post_id, korean_summary, summary_contract_version) values (%s, %s, %s)",
                (post_id, "합성 요약", 1),
            )
            cursor.execute(
                """
                insert into post_summary_role
                    (post_id, actor_name, responsibility, actor_type_code)
                values (%s, 'Summary Person', '검토', 'prov_person')
                """,
                (post_id,),
            )
            cursor.execute(migration.read_text(encoding="utf-8"))
            cursor.execute(
                """
                select mention_context
                  from post_person_mention
                 where post_id = %s and person_id = %s
                """,
                (post_id, summary_person_id),
            )
            keyman_row = cursor.fetchone()
            cursor.execute(
                """
                select count(*)
                  from post_summary_person_mention
                 where post_id = %s and person_id = %s
                """,
                (post_id, summary_person_id),
            )
            summary_count = cursor.fetchone()[0]
        connection.commit()
    finally:
        connection.close()

    assert keyman_row is not None
    assert keyman_row[0] == "Keyman extracted this mention from the synthetic body"
    assert summary_count == 1


async def _exercise_team_only_related_walk(
    database_dsn: str,
    first_post_id: str,
) -> None:
    """A team mentioned on two posts must walk even when one post has no people."""

    connection = await asyncpg.connect(database_dsn)
    try:
        author_id, corporate_entity_id = await connection.fetchrow(
            "select author_account_id, corporate_entity_id from source_post where post_id = $1",
            first_post_id,
        )
        second_post_id = str(
            await connection.fetchval(
                """
                insert into source_post
                    (author_account_id, corporate_entity_id, post_title, post_body,
                     voc_type_code, visibility_code)
                values ($1, $2, 'Team-only follow-up', '설계팀이 도면을 재검토했다.',
                        'voc', 'public')
                returning post_id
                """,
                author_id,
                corporate_entity_id,
            )
        )
        team_id = str(
            await connection.fetchval(
                """
                insert into cataloged_team (team_name, affiliated_organization_name)
                values ('설계팀', 'Synthetic Corp')
                returning team_id
                """
            )
        )
        await connection.execute(
            """
            insert into post_team_mention (post_id, team_id)
            values ($1, $2), ($3, $2)
            """,
            first_post_id,
            team_id,
            second_post_id,
        )
        async with connection.transaction():
            await persist_edges_for_post(connection, first_post_id)
            await persist_edges_for_post(connection, second_post_id)

        team_only_edges = await load_visible_subgraph(connection, [second_post_id])
        assert any(
            edge.edge_type_code == EDGE_MENTION_TEAM
            and edge.source_node_id == team_id
            and edge.target_node_id == second_post_id
            for edge in team_only_edges
        ), "a team-only post must still load its mention edge"

        related = await related_for_start(
            connection, NODE_TEAM, team_id, [first_post_id, second_post_id]
        )
        related_ids = {node["node_id"] for node in related}
        assert first_post_id in related_ids
        assert second_post_id in related_ids
        hydrated = await hydrate_related_nodes(
            connection, [(f"{NODE_TEAM}:{team_id}", 1.0)]
        )
        assert hydrated[0]["label"] == "설계팀"
        assert hydrated[0]["node_type_code"] == NODE_TEAM
    finally:
        await connection.close()


def test_team_only_posts_walk_related_nodes(projection_database: str) -> None:
    """ADR 0018: team mention edges must participate in the visible RWR walk."""

    database_dsn, post_id, _summary_person_id = projection_database.split("|")
    asyncio.run(_exercise_team_only_related_walk(database_dsn, post_id))


async def _exercise_homonym_organization_role_binding(
    database_dsn: str,
    post_id: str,
) -> None:
    """A same-named catalog org that this post did not resolve must stay off the role."""

    connection = await asyncpg.connect(database_dsn)
    try:
        mentioned_id = str(
            await connection.fetchval(
                """
                insert into corporate_entity
                    (corporate_entity_code, entity_name, entity_level_code)
                values ('HOMONYM-MENTIONED', 'Homonym Energy', 'company')
                returning corporate_entity_id
                """
            )
        )
        other_id = str(
            await connection.fetchval(
                """
                insert into corporate_entity
                    (corporate_entity_code, entity_name, entity_level_code)
                values ('HOMONYM-OTHER', 'Homonym Energy', 'company')
                returning corporate_entity_id
                """
            )
        )

        async def resolve_mentioned_organization(*_args, **_kwargs) -> str:
            return mentioned_id

        original = summary_ingestion.get_or_create_corporate_entity
        summary_ingestion.get_or_create_corporate_entity = resolve_mentioned_organization
        try:
            payload = await persist_post_summary(
                connection,
                post_id,
                PostSummary(
                    korean_summary="동명이인 조직이 일정만 확정했다.",
                    roles_and_responsibilities=(
                        RoleResponsibility(
                            actor_name="Homonym Energy",
                            responsibility="납품 일정 확정",
                            actor_type_code=ACTOR_TYPE_ORGANIZATION,
                        ),
                    ),
                ),
            )
        finally:
            summary_ingestion.get_or_create_corporate_entity = original

        roles = payload["roles_and_responsibilities"]
        assert len(roles) == 1
        assert roles[0]["catalog_node_id"] == mentioned_id
        assert roles[0]["catalog_node_type_code"] == NODE_CORPORATE_ENTITY
        fetched = await fetch_persisted_summary(connection, post_id)
        assert fetched is not None
        assert fetched["roles_and_responsibilities"][0]["catalog_node_id"] == mentioned_id
        assert fetched["roles_and_responsibilities"][0]["catalog_node_id"] != other_id
        mention_ids = [
            str(row["corporate_entity_id"])
            for row in await connection.fetch(
                "select corporate_entity_id from post_organization_mention "
                "where post_id = $1",
                post_id,
            )
        ]
        assert mention_ids == [mentioned_id]
    finally:
        await connection.close()


def test_homonym_organization_role_binds_the_resolved_catalog_id(
    projection_database: str,
) -> None:
    """ADR 0019: two catalog orgs can share a display name; the role keeps one id."""

    database_dsn, post_id, _summary_person_id = projection_database.split("|")
    asyncio.run(_exercise_homonym_organization_role_binding(database_dsn, post_id))


async def _exercise_same_name_person_catalog_order(
    database_dsn: str,
    post_id: str,
) -> None:
    """Two people with the same name must bind the earlier catalog row."""

    connection = await asyncpg.connect(database_dsn)
    try:
        earlier_id = str(
            await connection.fetchval(
                """
                insert into cataloged_person
                    (person_name, person_side_code, last_known_job_title, created_at)
                values (
                    'Kim Cheolsu', 'our_side', 'Sales Manager',
                    '2024-01-01T00:00:00+00'
                )
                returning person_id
                """
            )
        )
        await connection.execute(
            """
            insert into cataloged_person
                (person_name, person_side_code, last_known_job_title, created_at)
            values (
                'Kim Cheolsu', 'counterparty', 'Purchasing Lead',
                '2024-06-01T00:00:00+00'
            )
            """
        )
        await persist_post_summary(
            connection,
            post_id,
            PostSummary(
                korean_summary="김철수가 후속을 맡았다.",
                roles_and_responsibilities=(
                    RoleResponsibility(
                        actor_name="Kim Cheolsu",
                        responsibility="후속",
                        actor_type_code=ACTOR_TYPE_PERSON,
                    ),
                ),
            ),
        )
        payload = await fetch_persisted_summary(connection, post_id)
        assert payload is not None
        roles = payload["roles_and_responsibilities"]
        assert len(roles) == 1
        stored_id = str(
            await connection.fetchval(
                """
                select cataloged_person_id
                  from post_summary_role
                 where post_id = $1 and actor_name = 'Kim Cheolsu'
                """,
                post_id,
            )
        )
        assert stored_id == earlier_id
        assert roles[0]["catalog_node_id"] == earlier_id
        assert roles[0]["catalog_node_type_code"] == NODE_PERSON
    finally:
        await connection.close()


def test_same_name_person_roles_bind_the_earliest_catalog_row(
    projection_database: str,
) -> None:
    """ADR 0027: R&R person lookup must order by created_at, then person_id."""

    database_dsn, post_id, _summary_person_id = projection_database.split("|")
    asyncio.run(_exercise_same_name_person_catalog_order(database_dsn, post_id))

"""Real-integration test for the FastAPI backend: a genuine access token
from a live Keycloak, verified against Keycloak's live JWKS, against a
throwaway PostgreSQL database migrated with the actual schema file --
proving the OIDC + RBAC + ABAC path actually enforces what it claims to,
not just that the code type-checks.

Skipped unless both a local PostgreSQL server and a local Keycloak
(`docker compose up`, matching this repo's default ports) are reachable.

HTTP to Keycloak goes through ``lineageweave.http_client``.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import jwt
import psycopg2
import pytest
import redis

from lineageweave.http_client import HttpClientError, get_json, post_form

_POSTGRES_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
_KEYCLOAK_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL", "http://localhost:18080")
_VALKEY_URL = os.environ.get("LINEAGEWEAVE_TEST_VALKEY_URL", "redis://localhost:16379/0")
_REALM = "lineageweave-demo"
_MIGRATION_PATH = Path(__file__).resolve().parents[2] / "migrations" / "0001_initial_schema.sql"


def _postgres_available() -> bool:
    """True when a Postgres at the admin DSN accepts a connection."""
    try:
        psycopg2.connect(_POSTGRES_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


def _keycloak_available() -> bool:
    """True when the Keycloak realm's OIDC discovery document is reachable."""
    try:
        get_json(
            f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}/.well-known/openid-configuration",
            timeout=2,
        )
        return True
    except (HttpClientError, OSError, ValueError):
        return False


def _valkey_available() -> bool:
    """True when the Valkey instance at ``_VALKEY_URL`` responds to PING."""
    try:
        client = redis.from_url(_VALKEY_URL, socket_connect_timeout=2)
        try:
            return client.ping()
        finally:
            client.close()
    except redis.RedisError:
        return False


pytestmark = pytest.mark.skipif(
    not (_postgres_available() and _keycloak_available() and _valkey_available()),
    reason="requires a reachable local PostgreSQL, Keycloak, and Valkey -- run `make up` first",
)


def _fetch_demo_analyst_token() -> str:
    """Request a real resource-owner token for the synthetic demo.analyst user."""
    token_response = post_form(
        f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "lineageweave-frontend",
            "username": "demo.analyst",
            "password": "lineageweave-demo-only",
        },
        timeout=10,
    )
    return token_response["access_token"]


@pytest.fixture(scope="module")
def demo_analyst_token() -> str:
    return _fetch_demo_analyst_token()


@pytest.fixture
def seeded_db(demo_analyst_token):
    """A throwaway, freshly migrated database seeded with a user_account
    keyed to the real Keycloak demo.analyst subject, plus three source_post
    rows covering the three visibility outcomes the API must distinguish:
    public (visible to anyone), same-corp private (visible), and
    other-corp private (must NOT be visible).
    """
    subject = jwt.decode(demo_analyst_token, options={"verify_signature": False})["sub"]

    db_name = f"lineageweave_api_test_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(_POSTGRES_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f'create database "{db_name}"')

    db_dsn = _POSTGRES_ADMIN_DSN.rsplit("/", 1)[0] + f"/{db_name}"
    conn = psycopg2.connect(db_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(_MIGRATION_PATH.read_text())
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
                "('corporate_entity_level', 'group', 'Group'), "
                "('corporate_entity_level', 'company', 'Company'), "
                "('post_visibility', 'public', 'Public'), "
                "('post_visibility', 'private', 'Private'), "
                "('voc_type', 'voc', 'Voice of Customer'), "
                "('permission', 'post_read', 'Read posts'), "
                "('person_side', 'our_side', 'Our side'), "
                "('person_side', 'counterparty', 'Counterparty'), "
                "('node_type', 'node_person', 'Person'), "
                "('node_type', 'node_corporate_entity', 'Corporate entity'), "
                "('node_type', 'node_post', 'Post'), "
                "('edge_type', 'edge_mention', 'Mentioned in'), "
                "('edge_type', 'edge_affiliation', 'Affiliated with'), "
                "('edge_type', 'edge_co_mention', 'Co-mentioned'), "
                "('entity_relationship_type', 'rel_voc', 'Voice of Customer'), "
                "('entity_relationship_type', 'rel_vom', 'Voice of Market'), "
                "('entity_relationship_type', 'rel_vop', 'Voice of Partner'), "
                "('entity_relationship_type', 'rel_vocc', 'Voice of Customer''s Customer'), "
                "('entity_relationship_type', 'rel_voco', 'Voice of Competitor'), "
                "('entity_relationship_type', 'rel_vos', 'Voice of Supplier'), "
                "('ticket_status', 'open', 'Open'), "
                "('ticket_status', 'in_progress', 'In progress'), "
                "('ticket_status', 'closed', 'Closed'), "
                "('relation_verification_status', 'verify_pending', 'Not yet checked'), "
                "('relation_verification_status', 'verify_corroborated', 'Corroborated by external search'), "
                "('relation_verification_status', 'verify_uncorroborated', 'No corroborating evidence found'), "
                "('evaluation_criterion', 'general_sentiment_positive', 'Constructive stance'), "
                "('evaluation_criterion', 'general_sentiment_negative', 'Negative stance'), "
                "('evaluation_criterion', 'sales_lead_specificity', 'Sales-lead specificity')"
            )
            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('TEST-GROUP', 'Test Group', 'group') returning corporate_entity_id"
            )
            own_group_id = cur.fetchone()[0]
            cur.execute(
                "insert into corporate_entity (parent_entity_id, corporate_entity_code, entity_name, entity_level_code) "
                "values (%s, 'TEST-CORP', 'Test Corp', 'company') returning corporate_entity_id",
                (own_group_id,),
            )
            own_corp_id = cur.fetchone()[0]
            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('OTHER-CORP', 'Other Corp', 'group') returning corporate_entity_id"
            )
            other_corp_id = cur.fetchone()[0]

            cur.execute(
                "insert into user_account (external_subject_id, display_name, email_address) "
                "values (%s, 'Test Analyst', 'test.analyst@example.test') returning user_account_id",
                (subject,),
            )
            account_id = cur.fetchone()[0]
            cur.execute(
                "insert into account_affiliation (user_account_id, corporate_entity_id) values (%s, %s)",
                (account_id, own_corp_id),
            )
            cur.execute(
                "insert into access_role (role_code, role_name) values ('viewer', 'Viewer') returning access_role_id"
            )
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_read')",
                (role_id,),
            )
            cur.execute(
                "insert into account_role_assignment (user_account_id, access_role_id) values (%s, %s)",
                (account_id, role_id),
            )

            def _insert_post(title: str, corporate_entity_id, visibility_code: str, body: str = "body") -> str:
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, %s, 'voc', %s) returning post_id",
                    (account_id, corporate_entity_id, title, body, visibility_code),
                )
                return str(cur.fetchone()[0])

            public_post_id = _insert_post("Public post", other_corp_id, "public")
            own_private_post_id = _insert_post(
                "Own-corp private post",
                own_corp_id,
                "private",
                "Ada West at Test Corp followed up with Priya Nair at Northridge Grid about the delayed shipment. "
                "The weather in Gwangju was irrelevant.",
            )
            other_private_post_id = _insert_post("Other-corp private post", other_corp_id, "private")

            cur.execute(
                "insert into cataloged_person (person_name, person_side_code) values "
                "('Ada West', 'our_side') returning person_id"
            )
            our_person_id = str(cur.fetchone()[0])
            cur.execute(
                "insert into cataloged_person (person_name, person_side_code) values "
                "('Priya Nair', 'counterparty') returning person_id"
            )
            counterpart_person_id = str(cur.fetchone()[0])
            cur.execute(
                "insert into cataloged_person (person_name, person_side_code) values "
                "('Other Corp Only', 'counterparty') returning person_id"
            )
            hidden_person_id = str(cur.fetchone()[0])

            cur.execute(
                "insert into person_affiliation (person_id, affiliated_organization_name, affiliated_corporate_entity_id) "
                "values (%s, 'Test Corp', %s)",
                (our_person_id, own_corp_id),
            )
            cur.execute(
                "insert into person_affiliation (person_id, affiliated_organization_name) "
                "values (%s, 'Northridge Grid'), (%s, 'Northridge Holdings')",
                (counterpart_person_id, counterpart_person_id),
            )

            cur.execute(
                "insert into post_person_mention (post_id, person_id) values "
                "(%s, %s), (%s, %s), (%s, %s), (%s, %s)",
                (
                    own_private_post_id,
                    our_person_id,
                    own_private_post_id,
                    counterpart_person_id,
                    public_post_id,
                    our_person_id,
                    other_private_post_id,
                    hidden_person_id,
                ),
            )

            from lineageweave.knowledge_graph import knowledge_graph_edges_for_post

            seen_edges: set[tuple[str, str, str, str, str]] = set()
            for post_id, person_ids, affiliations in (
                (own_private_post_id, [our_person_id, counterpart_person_id], [(our_person_id, str(own_corp_id))]),
                (public_post_id, [our_person_id], [(our_person_id, str(own_corp_id))]),
                (other_private_post_id, [hidden_person_id], []),
            ):
                for edge in knowledge_graph_edges_for_post(post_id, person_ids, affiliations):
                    key = (
                        edge.source_node_type_code,
                        edge.source_node_id,
                        edge.target_node_type_code,
                        edge.target_node_id,
                        edge.edge_type_code,
                    )
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)
                    cur.execute(
                        "insert into knowledge_graph_edge ("
                        "source_node_type_code, source_node_id, target_node_type_code, "
                        "target_node_id, edge_type_code, edge_weight"
                        ") values (%s, %s, %s, %s, %s, %s)",
                        (
                            edge.source_node_type_code,
                            edge.source_node_id,
                            edge.target_node_type_code,
                            edge.target_node_id,
                            edge.edge_type_code,
                            edge.edge_weight,
                        ),
                    )
        conn.commit()

        yield {
            "dsn": db_dsn,
            "public_post_id": public_post_id,
            "own_group_id": str(own_group_id),
            "own_corp_id": str(own_corp_id),
            "own_private_post_id": own_private_post_id,
            "other_private_post_id": other_private_post_id,
            "our_person_id": our_person_id,
            "counterpart_person_id": counterpart_person_id,
            "hidden_person_id": hidden_person_id,
        }
    finally:
        conn.close()
        with admin_conn.cursor() as cur:
            cur.execute(f'drop database "{db_name}"')
        admin_conn.close()


@pytest.fixture
def client(seeded_db):
    os.environ["DATABASE_URL"] = seeded_db["dsn"]
    os.environ["KEYCLOAK_BASE_URL"] = _KEYCLOAK_BASE_URL
    os.environ["KEYCLOAK_ISSUER"] = f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}"

    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_me_reflects_the_authenticated_account(client, demo_analyst_token) -> None:
    response = client.get("/api/me", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Test Analyst"
    assert "post_read" in body["permission_codes"]


def test_post_list_includes_public_and_own_corp_but_excludes_other_corp(client, demo_analyst_token, seeded_db) -> None:
    response = client.get("/api/posts", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    titles = {post["post_title"] for post in response.json()}
    assert titles == {"Public post", "Own-corp private post"}


def test_persisted_summary_is_returned_without_an_llm(client, demo_analyst_token, seeded_db) -> None:
    """GET /api/posts/{id}/summary must serve a stored row even when the
    orchestrator is off -- otherwise a seeded demo popup stays empty.
    """
    os.environ.pop("ORCHESTRATOR_BASE_URL", None)
    os.environ.pop("ORCHESTRATOR_API_KEY", None)
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into post_summary_result (post_id, korean_summary) values (%s, %s)",
                (seeded_db["public_post_id"], "저장된 한국어 요약입니다."),
            )
            cur.execute(
                "insert into post_summary_event (post_id, event_ordinal, event_text) "
                "values (%s, 0, '저장된 이벤트')",
                (seeded_db["public_post_id"],),
            )
            cur.execute(
                "insert into post_summary_role (post_id, person_name, responsibility) "
                "values (%s, 'Ada West', '후속 연락')",
                (seeded_db["public_post_id"],),
            )
    finally:
        admin_conn.close()

    response = client.get(
        f"/api/posts/{seeded_db['public_post_id']}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["korean_summary"] == "저장된 한국어 요약입니다."
    assert body["key_events"] == ["저장된 이벤트"]
    assert body["roles_and_responsibilities"] == [
        {"person_name": "Ada West", "responsibility": "후속 연락"}
    ]


def test_seed_demo_summary_surfaces_on_get_summary(client, demo_analyst_token, seeded_db) -> None:
    """The same helper `make seed` calls must produce a row GET summary
    returns -- even with the orchestrator unset.
    """
    os.environ.pop("ORCHESTRATOR_BASE_URL", None)
    os.environ.pop("ORCHESTRATOR_API_KEY", None)
    from scripts.seed_demo_data import _seed_demo_public_summary

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            _seed_demo_public_summary(cur, seeded_db["public_post_id"])
    finally:
        admin_conn.close()

    response = client.get(
        f"/api/posts/{seeded_db['public_post_id']}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "에이다" in body["korean_summary"]
    assert body["key_events"]
    assert any(role["person_name"] == "Ada West" for role in body["roles_and_responsibilities"])


def test_seed_fixture_summaries_surface_on_get_summary(client, demo_analyst_token, seeded_db) -> None:
    """The A-100 fork and calendar commitment `make seed` writes must
    answer GET /api/posts/{id}/summary without a live orchestrator.
    """
    from scripts.seed_demo_data import (
        _seed_demo_calendar_commitment,
        _seed_fixture_summaries,
        insert_fixture_source_posts,
    )

    os.environ.pop("ORCHESTRATOR_BASE_URL", None)
    os.environ.pop("ORCHESTRATOR_API_KEY", None)
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('voc_type', 'vom', 'Voice of Market') "
                "on conflict (lookup_code) do nothing"
            )
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-SUMMARY', 'Summary thread' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            insert_fixture_source_posts(cur, author_id, corp_id, process_unit_id)
            _seed_demo_calendar_commitment(cur, author_id, corp_id, process_unit_id)
            _seed_fixture_summaries(cur)
            cur.execute(
                "select post_id from source_post where post_title = %s",
                ("Pricing renegotiation follow-up",),
            )
            fork_id = str(cur.fetchone()[0])
            cur.execute(
                "select post_id from source_post where post_title = %s",
                ("Follow-up on the Riverbend order confirmation",),
            )
            calendar_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    fork = client.get(
        f"/api/posts/{fork_id}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert fork.status_code == 200, fork.text
    assert "재협상" in fork.json()["korean_summary"]
    assert fork.json()["key_events"]

    calendar = client.get(
        f"/api/posts/{calendar_id}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert calendar.status_code == 200, calendar.text
    assert "리버벤드" in calendar.json()["korean_summary"]

    missing = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert missing.status_code == 503


def test_own_corp_private_post_detail_is_readable(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert response.status_code == 200
    assert "Test Corp" in response.json()["post_body"]


def test_other_corp_private_post_detail_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert response.status_code == 403


def test_nonexistent_post_is_not_found(client, demo_analyst_token) -> None:
    response = client.get(
        f"/api/posts/{uuid.uuid4()}", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert response.status_code == 404


def test_missing_token_is_unauthorized(client) -> None:
    response = client.get("/api/posts")
    assert response.status_code in (401, 403)


def test_forged_token_is_rejected(client) -> None:
    forged = jwt.encode({"sub": "not-a-real-subject", "iss": f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}"}, key="wrong-key", algorithm="HS256")
    response = client.get("/api/posts", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_own_corp_post_keymen_are_readable(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/keymen",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    names = {person["person_name"]: person for person in response.json()["keymen"]}
    assert set(names) == {"Ada West", "Priya Nair"}
    assert names["Ada West"]["person_side_code"] == "our_side"
    assert names["Ada West"]["person_side_label"] == "Our side"
    assert names["Priya Nair"]["person_side_code"] == "counterparty"
    assert names["Priya Nair"]["person_side_label"] == "Counterparty"
    assert {aff["organization_name"] for aff in names["Priya Nair"]["affiliations"]} == {
        "Northridge Grid",
        "Northridge Holdings",
    }


def test_other_corp_private_post_keymen_are_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/keymen",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_affiliate_tree_walks_ancestors_and_keeps_unresolved_orgs(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/affiliate-tree",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    trees = response.json()["trees"]
    names = [node["entity_name"] for node in trees]
    assert names[0] == "Test Group"
    assert trees[0]["entity_id"] == seeded_db["own_group_id"]
    assert trees[0]["resolved"] is True
    assert trees[0]["entity_level_label"] == "Group"
    children = trees[0]["children"]
    assert [child["entity_name"] for child in children] == ["Test Corp"]
    assert children[0]["entity_id"] == seeded_db["own_corp_id"]
    assert children[0]["entity_level_label"] == "Company"
    assert {person["person_name"] for person in children[0]["people"]} == {"Ada West"}
    assert children[0]["people"][0]["person_side_label"] == "Our side"
    unresolved = [node for node in trees if node["resolved"] is False]
    assert {node["entity_name"] for node in unresolved} == {"Northridge Grid", "Northridge Holdings"}
    assert all(person["person_name"] == "Priya Nair" for node in unresolved for person in node["people"])


def test_other_corp_private_affiliate_tree_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/affiliate-tree",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_voc_evidence_quotes_the_sentence_that_names_the_org(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/voc-evidence",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["voc_type_code"] == "voc"
    assert body["voc_type_label"] == "Voice of Customer"
    assert body["excerpts"] == [
        "Ada West at Test Corp followed up with Priya Nair at Northridge Grid about the delayed shipment."
    ]
    assert "weather" not in " ".join(body["excerpts"]).lower()
    assert body["counterparties"] == []


def test_other_corp_private_voc_evidence_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/voc-evidence",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_related_keymen_use_rwr_and_hide_invisible_posts(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/keymen/{seeded_db['our_person_id']}/related",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["person_name"] == "Ada West"
    related_ids = {node["node_id"] for node in body["related"]}
    assert seeded_db["counterpart_person_id"] in related_ids
    assert seeded_db["own_private_post_id"] in related_ids
    assert seeded_db["hidden_person_id"] not in related_ids
    assert seeded_db["other_private_post_id"] not in related_ids
    assert all(node["relevance"] > 0 for node in body["related"])
    by_id = {node["node_id"]: node for node in body["related"]}
    counterpart = by_id[seeded_db["counterpart_person_id"]]
    assert counterpart["ontology_label"] == "Person"
    assert counterpart["ontology_iri"].endswith("#Person")
    own_post = by_id[seeded_db["own_private_post_id"]]
    assert own_post["ontology_label"] == "Post"


def test_keyman_only_on_other_corp_private_post_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/keymen/{seeded_db['hidden_person_id']}/related",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_extract_keymen_requires_post_admin(client, demo_analyst_token, seeded_db) -> None:
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/extract-keymen",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_extract_keymen_persists_a_real_llm_extraction(client, demo_analyst_token, seeded_db) -> None:
    """The full write path, end to end: a real LLM call through a live
    contextual-orchestrator, persisted to Postgres, then read back through
    the read endpoints -- not a mocked extraction client.
    """
    os.environ["ORCHESTRATOR_BASE_URL"] = _ORCHESTRATOR_BASE_URL
    os.environ["ORCHESTRATOR_API_KEY"] = _ORCHESTRATOR_API_KEY

    from lineageweave.fixtures import ambiguous_keyman_post

    title, body = ambiguous_keyman_post()

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                "from source_post where post_id = %s "
                "returning post_id",
                (title, body, seeded_db["own_private_post_id"]),
            )
            new_post_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    response = client.post(
        f"/api/posts/{new_post_id}/extract-keymen",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert body_json["extracted_count"] >= 2
    names = {mention["person_name"] for mention in body_json["mentions"]}
    assert any("Jordan" in name for name in names)
    assert any("Priya" in name for name in names)

    keymen_response = client.get(
        f"/api/posts/{new_post_id}/keymen", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert keymen_response.status_code == 200
    persisted_names = {person["person_name"] for person in keymen_response.json()["keymen"]}
    assert persisted_names == names

    # ambiguous_keyman_post's Priya Nair is affiliated with "Northridge
    # Grid" and "Northridge Holdings" -- extract-keymen should have fed
    # those into the entity-relationship classifier and persisted a real
    # classification for each, readable back via the counterparties endpoint.
    counterparty_names = {c["organization_name"] for c in body_json["counterparties"]}
    assert counterparty_names == {"Northridge Grid", "Northridge Holdings"}
    valid_codes = {"rel_voc", "rel_vom", "rel_vop", "rel_vocc", "rel_voco", "rel_vos"}
    assert all(c["relationship_type_code"] in valid_codes for c in body_json["counterparties"])

    counterparties_response = client.get(
        f"/api/posts/{new_post_id}/counterparties", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert counterparties_response.status_code == 200
    persisted_counterparty_names = {
        c["counterparty_entity_name"] for c in counterparties_response.json()["counterparties"]
    }
    assert persisted_counterparty_names == counterparty_names


_SEARXNG_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_SEARXNG_BASE_URL", "http://localhost:18888")


def _searxng_available() -> bool:
    """True when a Searxng instance at `_SEARXNG_BASE_URL` answers a JSON
    search. A generous timeout: a real search round-trips through several
    real upstream search engines, genuinely slower than a local health
    check.
    """
    try:
        get_json(f"{_SEARXNG_BASE_URL}/search?q=ping&format=json", timeout=10)
        return True
    except (HttpClientError, OSError, ValueError):
        return False


@pytest.mark.skipif(
    not _searxng_available(),
    reason="requires a reachable local Searxng -- run `docker compose up searxng` first",
)
def test_verify_relations_persists_real_search_outcomes(client, demo_analyst_token, seeded_db) -> None:
    """A real end-to-end proof of relation_verification.py's search-backed
    check: a real, well-known organization name gets `verify_corroborated`
    with a real evidence URL, and a deliberately fabricated organization
    name gets `verify_uncorroborated` with none -- not a mocked search
    client, a genuine Searxng round trip through
    POST /api/posts/{id}/verify-relations.
    """
    os.environ["SEARXNG_BASE_URL"] = _SEARXNG_BASE_URL

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into post_counterparty_entity (post_id, counterparty_entity_name, relationship_type_code) "
                "values (%s, 'Wikipedia', 'rel_voc'), "
                "(%s, 'Zzqxvthorp Fictitious Nonexistent Org 8f3e1c', 'rel_voco')",
                (seeded_db["public_post_id"], seeded_db["public_post_id"]),
            )
    finally:
        admin_conn.close()

    response = client.post(
        f"/api/posts/{seeded_db['public_post_id']}/verify-relations",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    verified = {row["counterparty_entity_name"]: row for row in response.json()["verified"]}

    real_org = verified["Wikipedia"]
    if real_org["verification_status_code"] != "verify_corroborated":
        pytest.skip(
            "Searxng answered JSON but produced no non-search host/snippet "
            "for a known org -- upstream engines are empty or blocked"
        )
    assert real_org["verification_evidence_url"]

    fake_org = verified["Zzqxvthorp Fictitious Nonexistent Org 8f3e1c"]
    assert fake_org["verification_status_code"] == "verify_uncorroborated"
    assert fake_org["verification_evidence_url"] is None

    counterparties_response = client.get(
        f"/api/posts/{seeded_db['public_post_id']}/counterparties",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    persisted = {c["counterparty_entity_name"]: c for c in counterparties_response.json()["counterparties"]}
    assert persisted["Wikipedia"]["verification_status_code"] == "verify_corroborated"
    assert persisted["Zzqxvthorp Fictitious Nonexistent Org 8f3e1c"]["verification_status_code"] == "verify_uncorroborated"

    # Already-checked rows are left alone on a second call, not re-searched.
    second_response = client.post(
        f"/api/posts/{seeded_db['public_post_id']}/verify-relations",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert second_response.json()["verified"] == []


def test_evaluation_is_empty_before_a_judge_run(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['public_post_id']}/evaluation",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["responses"] == []


def test_evaluate_is_unavailable_without_orchestrator(client, demo_analyst_token, seeded_db) -> None:
    os.environ.pop("ORCHESTRATOR_BASE_URL", None)
    os.environ.pop("ORCHESTRATOR_API_KEY", None)
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
    finally:
        admin_conn.close()
    response = client.post(
        f"/api/posts/{seeded_db['public_post_id']}/evaluate",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 503


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_extract_keymen_normalizes_html_and_embedded_image_content(
    client, demo_analyst_token, seeded_db
) -> None:
    """A real end-to-end proof that HTML/base64-image post bodies are
    normalized (lineageweave.post_content_normalization) before the LLM
    ever sees them: the same real people from ambiguous_keyman_post()
    must still be found even though the post body is wrapped in HTML
    formatting and carries an embedded image, which a raw-body call
    would either choke the model's attention on (literal tags) or bloat
    the prompt with (raw base64) -- see backend/app/main.py's
    extract-keymen endpoint and ADR-referenced design in
    lineageweave/post_content_normalization.py.
    """
    os.environ["ORCHESTRATOR_BASE_URL"] = _ORCHESTRATOR_BASE_URL
    os.environ["ORCHESTRATOR_API_KEY"] = _ORCHESTRATOR_API_KEY

    from lineageweave.fixtures import ambiguous_keyman_post

    title, plain_body = ambiguous_keyman_post()
    # A 1x1 PNG data URI -- real base64 image bytes, not a fake string.
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    html_body = (
        f'<div style="color:red;font-weight:bold"><p>{plain_body}</p>'
        f'<img src="data:image/png;base64,{tiny_png_b64}"/></div>'
    )

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                "from source_post where post_id = %s "
                "returning post_id",
                (title, html_body, seeded_db["own_private_post_id"]),
            )
            new_post_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    response = client.post(
        f"/api/posts/{new_post_id}/extract-keymen",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    names = {mention["person_name"] for mention in response.json()["mentions"]}
    # The real people are still findable through the HTML/image wrapping --
    # proof the LLM received clean text, not raw markup or base64 noise
    # drowning out the actual content.
    assert any("Jordan" in name for name in names)
    assert any("Priya" in name for name in names)


def test_counterparties_endpoint_is_empty_before_extraction(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/counterparties",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    assert response.json()["counterparties"] == []


def test_other_corp_private_post_counterparties_are_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/counterparties",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_unknown_keyman_is_not_found(client, demo_analyst_token) -> None:
    response = client.get(
        f"/api/keymen/{uuid.uuid4()}/related",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 404


def test_post_lineage_surfaces_indirect_link_via_shared_keyman(client, demo_analyst_token, seeded_db) -> None:
    """No live orchestrator needed -- this is pure DB + graph-math, no LLM
    call. own_private_post_id and public_post_id share no post_lineage_edge
    but both mention our_person_id (Ada West); the other-corp private
    post (hidden_person_id, a DIFFERENT person, no shared Keyman with
    either) must not appear at all.
    """
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/lineage",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["direct"] == []
    indirect_ids = {post["post_id"] for post in body["indirect"]}
    assert indirect_ids == {seeded_db["public_post_id"]}


def test_other_corp_private_post_summary_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_other_corp_private_post_chat_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    response = client.post(
        f"/api/posts/{seeded_db['other_private_post_id']}/chat",
        json={"question": "what happened"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_post_summary_returns_a_real_korean_summary(client, demo_analyst_token, seeded_db) -> None:
    os.environ["ORCHESTRATOR_BASE_URL"] = _ORCHESTRATOR_BASE_URL
    os.environ["ORCHESTRATOR_API_KEY"] = _ORCHESTRATOR_API_KEY

    from lineageweave.fixtures import ambiguous_keyman_post

    title, body = ambiguous_keyman_post()
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                "from source_post where post_id = %s returning post_id",
                (title, body, seeded_db["own_private_post_id"]),
            )
            new_post_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    response = client.get(
        f"/api/posts/{new_post_id}/summary", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert any("가" <= ch <= "힣" for ch in body_json["korean_summary"])
    assert len(body_json["key_events"]) >= 1


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_post_chat_cites_a_post_linked_only_via_a_shared_keyman(client, demo_analyst_token, seeded_db) -> None:
    """The real end-to-end proof of Phase 4's Event Lineage chat: two
    posts with no direct lineage edge between them, linked only by a
    shared Keyman -- the retrieve step must pull the second post in via
    the Knowledge Graph, and the answer must cite it, because the
    question can only be answered by combining both.
    """
    os.environ["ORCHESTRATOR_BASE_URL"] = _ORCHESTRATOR_BASE_URL
    os.environ["ORCHESTRATOR_API_KEY"] = _ORCHESTRATOR_API_KEY

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_account_id, corporate_entity_id = cur.fetchone()

            def _insert_post(title, body):
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, %s, 'voc', 'public') returning post_id",
                    (author_account_id, corporate_entity_id, title, body),
                )
                return str(cur.fetchone()[0])

            post_a = _insert_post("Kickoff call", "We agreed to submit the transformer bid by March 3.")
            post_b = _insert_post("Bid follow-up", "The client requested a revised quote, sent March 12.")

            cur.execute(
                "insert into cataloged_person (person_name, person_side_code) values ('Shared Keyman', 'our_side') "
                "returning person_id"
            )
            shared_person_id = str(cur.fetchone()[0])
            cur.execute(
                "insert into post_person_mention (post_id, person_id) values (%s, %s), (%s, %s)",
                (post_a, shared_person_id, post_b, shared_person_id),
            )

            from lineageweave.knowledge_graph import knowledge_graph_edges_for_post

            for post_id in (post_a, post_b):
                for edge in knowledge_graph_edges_for_post(post_id, [shared_person_id]):
                    cur.execute(
                        "insert into knowledge_graph_edge (source_node_type_code, source_node_id, "
                        "target_node_type_code, target_node_id, edge_type_code, edge_weight) "
                        "values (%s, %s, %s, %s, %s, %s)",
                        (
                            edge.source_node_type_code,
                            edge.source_node_id,
                            edge.target_node_type_code,
                            edge.target_node_id,
                            edge.edge_type_code,
                            edge.edge_weight,
                        ),
                    )
    finally:
        admin_conn.close()

    response = client.post(
        f"/api/posts/{post_a}/chat",
        json={"question": "What happened with the bid between the kickoff and now?"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert set(body_json["source_post_ids"]) == {post_a, post_b}
    assert post_b in body_json["cited_post_ids"]
    cited_by_id = {row["post_id"]: row["post_title"] for row in body_json["cited_posts"]}
    assert cited_by_id[post_b] == "Bid follow-up"


def test_rebuild_lineage_requires_post_admin(client, demo_analyst_token) -> None:
    response = client.post("/api/lineage/rebuild", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 403


def test_rebuild_lineage_recovers_the_a100_fork(client, demo_analyst_token, seeded_db) -> None:
    """Rebuild on the same A-100+B-200 rows seed writes (grouping keys +
    occurred_at), not a hand-picked A-100-only insert that hides mapping bugs.
    """
    from scripts.seed_demo_data import insert_fixture_source_posts

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts'), "
                "('voc_type', 'vom', 'Voice of Market') "
                "on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-LINEAGE', 'Lineage thread' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            insert_fixture_source_posts(cur, author_id, corp_id, process_unit_id)
    finally:
        admin_conn.close()

    rebuild = client.post("/api/lineage/rebuild", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["edge_count"] >= 2

    graph = client.get("/api/lineage", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert graph.status_code == 200
    body = graph.json()
    nodes = {node["label"]: node for node in body["nodes"]}
    fork = nodes["Pricing renegotiation follow-up"]
    assert fork["is_branch_point"] is True
    assert fork["group"] == "A-100"
    children = {
        next(node["label"] for node in body["nodes"] if node["id"] == edge["target"])
        for edge in body["edges"]
        if edge["source"] == fork["id"]
    }
    assert "Pricing renegotiation: revised quote sent" in children
    assert "Delivery schedule question raised" in children
    assert nodes["Unrelated: annual account review"]["is_root"] is True
    assert nodes["Unrelated: annual account review"]["group"] == "A-100"
    assert nodes["Technical specification review meeting"]["group"] == "B-200"

    per_post = client.get(
        f"/api/posts/{fork['id']}/lineage",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert per_post.status_code == 200
    direct_titles = {post["post_title"] for post in per_post.json()["direct"]}
    assert "Pricing renegotiation: revised quote sent" in direct_titles
    assert "Delivery schedule question raised" in direct_titles


def test_lineage_graph_hides_other_corp_private_posts(client, demo_analyst_token, seeded_db) -> None:
    response = client.get("/api/lineage", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    ids = {node["id"] for node in response.json()["nodes"]}
    assert seeded_db["public_post_id"] in ids
    assert seeded_db["own_private_post_id"] in ids
    assert seeded_db["other_private_post_id"] not in ids


def _grant_post_admin(dsn: str) -> None:
    """Same ad-hoc grant every post_admin-gated test in this file uses:
    the base fixture only seeds `post_read`.
    """
    admin_conn = psycopg2.connect(dsn)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
    finally:
        admin_conn.close()


def test_tickets_list_is_empty_before_any_created(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    assert response.json()["tickets"] == []


def test_create_ticket_requires_post_admin(client, demo_analyst_token, seeded_db) -> None:
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Follow up on pricing", "ticket_status_code": "open"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_other_corp_private_post_tickets_are_forbidden(client, demo_analyst_token, seeded_db) -> None:
    list_response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/tickets",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert list_response.status_code == 403

    _grant_post_admin(seeded_db["dsn"])
    create_response = client.post(
        f"/api/posts/{seeded_db['other_private_post_id']}/tickets",
        json={"ticket_title": "Should not be creatable", "ticket_status_code": "open"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert create_response.status_code == 403


def test_create_ticket_with_invalid_status_code_is_422(client, demo_analyst_token, seeded_db) -> None:
    _grant_post_admin(seeded_db["dsn"])
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Bad status", "ticket_status_code": "not_a_real_status"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 422


def test_create_list_and_patch_ticket_end_to_end(client, demo_analyst_token, seeded_db) -> None:
    """The full CRUD path against a live Postgres: create a ticket on a
    visible post, confirm it's listed, PATCH its status and assignee, and
    confirm the change is reflected on the next GET.
    """
    _grant_post_admin(seeded_db["dsn"])

    create_response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Confirm delivery window", "ticket_status_code": "open"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["ticket_status_code"] == "open"
    assert created["ticket_title"] == "Confirm delivery window"
    assert created["assigned_account_id"] is None
    ticket_id = created["issue_ticket_id"]

    list_response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert list_response.status_code == 200
    listed_ids = {ticket["issue_ticket_id"] for ticket in list_response.json()["tickets"]}
    assert ticket_id in listed_ids

    patch_response = client.patch(
        f"/api/tickets/{ticket_id}",
        json={"ticket_status_code": "closed"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["ticket_status_code"] == "closed"

    reread_response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    reread_ticket = next(t for t in reread_response.json()["tickets"] if t["issue_ticket_id"] == ticket_id)
    assert reread_ticket["ticket_status_code"] == "closed"


def test_patch_ticket_requires_post_admin(client, demo_analyst_token, seeded_db) -> None:
    _grant_post_admin(seeded_db["dsn"])
    create_response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Needs admin to edit", "ticket_status_code": "open"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    ticket_id = create_response.json()["issue_ticket_id"]

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "delete from role_permission where access_role_id = %s and permission_code = 'post_admin'",
                (role_id,),
            )
    finally:
        admin_conn.close()

    response = client.patch(
        f"/api/tickets/{ticket_id}",
        json={"ticket_status_code": "closed"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_patch_unknown_ticket_is_not_found(client, demo_analyst_token, seeded_db) -> None:
    _grant_post_admin(seeded_db["dsn"])
    response = client.patch(
        f"/api/tickets/{uuid.uuid4()}",
        json={"ticket_status_code": "closed"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 404


def test_patch_ticket_on_other_corp_private_post_is_forbidden(client, demo_analyst_token, seeded_db) -> None:
    """A ticket has no visibility_code of its own -- ABAC must resolve to
    the ticket's OWNING post before deciding, not skip the check because
    the ticket row itself has no corporate_entity_id.
    """
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into issue_ticket (post_id, ticket_status_code, ticket_title) "
                "values (%s, 'open', 'Ticket on a post this account cannot see') "
                "returning issue_ticket_id",
                (seeded_db["other_private_post_id"],),
            )
            ticket_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    _grant_post_admin(seeded_db["dsn"])
    response = client.patch(
        f"/api/tickets/{ticket_id}",
        json={"ticket_status_code": "closed"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_post_activity_is_empty_before_any_mutation(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/activity",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200
    assert response.json()["events"] == []


def test_ticket_mutations_publish_real_events_to_the_activity_feed(
    client, demo_analyst_token, seeded_db
) -> None:
    """Proves Valkey is genuinely load-bearing: a ticket create/patch
    through the real HTTP API is independently observable afterward on
    ``GET /api/posts/{post_id}/activity``, which reads straight off the
    live Valkey stream (no DB involvement in the read path).
    """
    _grant_post_admin(seeded_db["dsn"])

    create_response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Confirm freight terms", "ticket_status_code": "open"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    ticket_id = create_response.json()["issue_ticket_id"]

    client.patch(
        f"/api/tickets/{ticket_id}",
        json={"ticket_status_code": "in_progress"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )

    activity_response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}/activity",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert activity_response.status_code == 200
    events = activity_response.json()["events"]
    assert len(events) == 2
    # XREVRANGE returns newest first: the status change comes before the
    # creation event.
    assert events[0]["event_type"] == "ticket_status_changed"
    assert "in_progress" in events[0]["summary"]
    assert events[1]["event_type"] == "ticket_created"
    assert "Confirm freight terms" in events[1]["summary"]


def test_post_activity_on_other_corp_private_post_is_forbidden(
    client, demo_analyst_token, seeded_db
) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['other_private_post_id']}/activity",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_derive_commitment_requires_post_admin(client, demo_analyst_token, seeded_db) -> None:
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/derive-commitment",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_calendar_is_empty_before_any_commitment(client, demo_analyst_token, seeded_db) -> None:
    response = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    assert response.json()["commitments"] == []


def test_calendar_hides_other_corp_private_commitments_and_sorts_by_due_date(
    client, demo_analyst_token, seeded_db
) -> None:
    """Two dated tickets inserted directly (own-corp private and
    other-corp private, in reverse due-date order); the calendar must
    show only the visible one, proving both the ABAC filter and the
    soonest-first ordering.
    """
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into issue_ticket (post_id, ticket_status_code, ticket_title, due_date, commitment_summary) "
                "values (%s, 'open', 'Visible commitment', '2026-03-01', 'Send the revised quote')",
                (seeded_db["own_private_post_id"],),
            )
            cur.execute(
                "insert into issue_ticket (post_id, ticket_status_code, ticket_title, due_date, commitment_summary) "
                "values (%s, 'open', 'Hidden commitment', '2026-01-01', 'Should never be visible')",
                (seeded_db["other_private_post_id"],),
            )
    finally:
        admin_conn.close()

    response = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    commitments = response.json()["commitments"]
    assert len(commitments) == 1
    assert commitments[0]["ticket_title"] == "Visible commitment"
    assert commitments[0]["due_date"] == "2026-03-01"
    assert commitments[0]["commitment_summary"] == "Send the revised quote"
    assert "visibility_code" not in commitments[0]
    assert "corporate_entity_id" not in commitments[0]


def test_calendar_excludes_closed_tickets_and_includes_manual_due_dates(
    client, demo_analyst_token, seeded_db
) -> None:
    """A closed dated ticket is done work, not a calendar item; a
    still-open ticket created through the regular ticket API with a
    due_date must still appear -- the calendar is every dated open
    ticket, not only LLM-derived ones.
    """
    _grant_post_admin(seeded_db["dsn"])
    closed = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={
            "ticket_title": "Already done",
            "ticket_status_code": "open",
            "due_date": "2026-02-01",
        },
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert closed.status_code == 201, closed.text
    patch = client.patch(
        f"/api/tickets/{closed.json()['issue_ticket_id']}",
        json={"ticket_status_code": "closed"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert patch.status_code == 200
    opened = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={
            "ticket_title": "Still open",
            "ticket_status_code": "open",
            "due_date": "2026-04-01",
        },
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert opened.status_code == 201, opened.text

    response = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200
    titles = [c["ticket_title"] for c in response.json()["commitments"]]
    assert "Still open" in titles
    assert "Already done" not in titles


def test_create_ticket_with_malformed_due_date_is_422(client, demo_analyst_token, seeded_db) -> None:
    _grant_post_admin(seeded_db["dsn"])
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/tickets",
        json={"ticket_title": "Bad date", "ticket_status_code": "open", "due_date": "next Friday"},
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 422


def test_derive_commitment_unavailable_without_orchestrator(
    client, demo_analyst_token, seeded_db, monkeypatch
) -> None:
    """Null client must 503, not invent a commitment."""
    from lineageweave.commitment_extraction import NullCommitmentExtractionClient

    _grant_post_admin(seeded_db["dsn"])
    monkeypatch.setattr(
        "backend.app.main._commitment_extraction_client",
        lambda: NullCommitmentExtractionClient(),
    )
    response = client.post(
        f"/api/posts/{seeded_db['own_private_post_id']}/derive-commitment",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 503


def test_derive_commitment_uses_post_created_at_and_does_not_duplicate(
    client, demo_analyst_token, seeded_db, monkeypatch
) -> None:
    """CI-stable persist path: a fake client still has to receive the
    post's document-creation date (not wall-clock now) and a second
    derive must refresh the same ticket instead of stacking another.
    """
    from lineageweave.commitment_extraction import CustomerCommitment

    _grant_post_admin(seeded_db["dsn"])

    class _FakeClient:
        available = True
        seen_reference_dates: list[str] = []

        def extract(self, post_title: str, post_body: str, reference_date: str) -> CustomerCommitment:
            self.seen_reference_dates.append(reference_date)
            return CustomerCommitment(
                has_commitment=True,
                commitment_summary="Send Riverbend the revised delivery schedule.",
                due_date="2026-01-09",
            )

    fake = _FakeClient()
    monkeypatch.setattr("backend.app.main._commitment_extraction_client", lambda: fake)

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, post_title, post_body, "
                "voc_type_code, visibility_code, created_at) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public', %s "
                "from source_post where post_id = %s "
                "returning post_id",
                (
                    "Follow-up on the Riverbend order confirmation",
                    "We still owe Riverbend the revised delivery schedule by next Friday.",
                    "2026-01-05T00:00:00+00",
                    seeded_db["own_private_post_id"],
                ),
            )
            new_post_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    first = client.post(
        f"/api/posts/{new_post_id}/derive-commitment",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert first.status_code == 200, first.text
    first_ticket = first.json()["ticket"]
    assert first.json()["has_commitment"] is True
    assert first_ticket["due_date"] == "2026-01-09"
    assert fake.seen_reference_dates == ["2026-01-05"]

    fake.seen_reference_dates.clear()
    second = client.post(
        f"/api/posts/{new_post_id}/derive-commitment",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["ticket"]["issue_ticket_id"] == first_ticket["issue_ticket_id"]

    listed = client.get(
        f"/api/posts/{new_post_id}/tickets",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert len(listed.json()["tickets"]) == 1

    calendar = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    ticket_ids = {c["issue_ticket_id"] for c in calendar.json()["commitments"]}
    assert first_ticket["issue_ticket_id"] in ticket_ids


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_derive_commitment_persists_a_real_llm_derivation(client, demo_analyst_token, seeded_db) -> None:
    """The full write path, end to end: a real LLM call through a live
    contextual-orchestrator resolves a relative deadline ("by next
    Friday") against a reference date, persists it as an issue_ticket,
    and the calendar surfaces it -- not a mocked extraction client.
    """
    os.environ["ORCHESTRATOR_BASE_URL"] = _ORCHESTRATOR_BASE_URL
    os.environ["ORCHESTRATOR_API_KEY"] = _ORCHESTRATOR_API_KEY

    from lineageweave.fixtures import ambiguous_commitment_post

    title, body = ambiguous_commitment_post()

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
                "values ('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                "from source_post where post_id = %s "
                "returning post_id",
                (title, body, seeded_db["own_private_post_id"]),
            )
            new_post_id = str(cur.fetchone()[0])
    finally:
        admin_conn.close()

    response = client.post(
        f"/api/posts/{new_post_id}/derive-commitment",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    body_json = response.json()
    assert body_json["has_commitment"] is True
    assert body_json["ticket"]["due_date"] is not None
    assert body_json["ticket"]["commitment_summary"]

    calendar_response = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    ticket_ids = {c["issue_ticket_id"] for c in calendar_response.json()["commitments"]}
    assert body_json["ticket"]["issue_ticket_id"] in ticket_ids


def test_seed_calendar_commitment_surfaces_on_get_calendar(client, demo_analyst_token, seeded_db) -> None:
    """The same helper `make seed` calls must produce a row GET /api/calendar
    returns -- due 2026-01-09 against the Riverbend fixture created 2026-01-05.
    """
    from scripts.seed_demo_data import _seed_demo_calendar_commitment

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-CAL', 'Calendar seed unit' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            _seed_demo_calendar_commitment(cur, author_id, corp_id, process_unit_id)
    finally:
        admin_conn.close()

    response = client.get("/api/calendar", headers={"Authorization": f"Bearer {demo_analyst_token}"})
    assert response.status_code == 200, response.text
    commitments = response.json()["commitments"]
    dues = {c["due_date"] for c in commitments}
    assert "2026-01-09" in dues
    titles = {c["post_title"] for c in commitments}
    from lineageweave.fixtures import ambiguous_commitment_post

    expected_title, _ = ambiguous_commitment_post()
    assert expected_title in titles


def test_seed_period_report_surfaces_on_get_reports(client, demo_analyst_token, seeded_db) -> None:
    """The same helper `make seed` calls must produce a 2026-W02 report
    GET /api/reports returns -- high-band posts outrank low-band posts
    on the fitted EAP metric.
    """
    from scripts.seed_demo_data import _seed_demo_period_report

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-SEED-REPORT', 'Report seed unit' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            _seed_demo_period_report(cur, author_id, corp_id, process_unit_id)
    finally:
        admin_conn.close()

    response = client.get(
        "/api/reports/process_unit/2026-W02",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    reports = response.json()["reports"]
    assert len(reports) >= 2
    high_report = next(
        report for report in reports if any(m["post_title"].startswith("High-band") for m in report["members"])
    )
    low_report = next(
        report for report in reports if any(m["post_title"].startswith("Low-band") for m in report["members"])
    )
    assert high_report["mean_theta"] > low_report["mean_theta"]
    assert high_report["link_method"] == "fipc"
    assert high_report["selected_model"] in {"grm", "gpcm"}
    assert high_report["delta_mean_theta"] is None

    week3 = client.get(
        "/api/reports/process_unit/2026-W03",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert week3.status_code == 200, week3.text
    linked = week3.json()["reports"]
    assert linked
    assert linked[0]["link_method"] == "fipc"
    assert linked[0]["anchor_period_code"] == "2026-W02"
    assert linked[0]["mean_theta"] > low_report["mean_theta"]

    index = client.get(
        "/api/reports/process_unit",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert index.status_code == 200, index.text
    periods = {row["period_code"] for row in index.json()["periods"]}
    assert {"2026-W02", "2026-W03"} <= periods

    compare = client.get(
        "/api/reports/compare/2026-W02",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert compare.status_code == 200, compare.text
    kinds = {row["grouping_kind"] for row in compare.json()["groupings"]}
    assert {"process_unit", "corporate_entity", "thread_group"} <= kinds
    threads = {
        row["grouping_label"]: row["mean_theta"]
        for row in compare.json()["groupings"]
        if row["grouping_kind"] == "thread_group"
    }
    assert threads["A-100"] > threads["B-200"]


def test_rebuild_reports_requires_post_admin(client, demo_analyst_token) -> None:
    response = client.post(
        "/api/reports/process_unit/2026-W02/rebuild",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 403


def test_reports_reject_unknown_period(client, demo_analyst_token) -> None:
    response = client.get(
        "/api/reports/process_unit/not-a-period",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 422


def test_period_report_high_posts_outrank_low_posts(client, demo_analyst_token, seeded_db) -> None:
    """Insert constructed high/low IRT rows, rebuild, and read GET /api/reports.

    The numbers must come from the fitted EAP metric: high-category posts
    outscore low-category posts in the same process unit and ISO week.
    """
    from datetime import datetime, timezone

    from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
                "('permission', 'post_admin', 'Administer posts'), "
                "('evaluation_criterion', 'general_sentiment_positive', 'Constructive stance'), "
                "('evaluation_criterion', 'general_sentiment_negative', 'Negative stance'), "
                "('evaluation_criterion', 'sales_lead_specificity', 'Sales-lead specificity') "
                "on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-REPORT', 'Report unit' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            created = datetime(2026, 1, 5, tzinfo=timezone.utc)
            post_ids = {"high": [], "low": []}
            for band, category in (("high", IRT_CATEGORY_COUNT - 1), ("low", 0)):
                for idx in range(4):
                    cur.execute(
                        "insert into source_post "
                        "(author_account_id, corporate_entity_id, process_unit_id, "
                        " post_title, post_body, voc_type_code, visibility_code, created_at) "
                        "values (%s, %s, %s, %s, 'body', 'voc', 'public', %s) returning post_id",
                        (author_id, corp_id, process_unit_id, f"{band} report post {idx}", created),
                    )
                    post_id = cur.fetchone()[0]
                    post_ids[band].append(str(post_id))
                    for code in CRITERION_CODES:
                        cur.execute(
                            "insert into post_evaluation_response "
                            "(post_id, criterion_code, rubric_version, response_category) "
                            "values (%s, %s, '2026-08-13', %s)",
                            (post_id, code, category),
                        )
    finally:
        admin_conn.close()

    rebuild = client.post(
        "/api/reports/process_unit/2026-W02/rebuild",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["group_count"] >= 1

    response = client.get(
        "/api/reports/process_unit/2026-W02",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    reports = response.json()["reports"]
    assert reports
    members = {member["post_title"]: member["theta_eap"] for member in reports[0]["members"]}
    high_mean = sum(theta for title, theta in members.items() if title.startswith("high")) / 4
    low_mean = sum(theta for title, theta in members.items() if title.startswith("low")) / 4
    assert high_mean > low_mean
    assert reports[0]["selected_model"] in {"grm", "gpcm"}
    assert reports[0]["post_count"] == 8
    assert reports[0]["link_method"] == "fipc"

    created_w03 = datetime(2026, 1, 12, tzinfo=timezone.utc)
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "select author_account_id, corporate_entity_id, process_unit_id "
                "from source_post where post_title = 'high report post 0'"
            )
            author_id, corp_id, process_unit_id = cur.fetchone()
            for idx in range(6):
                cur.execute(
                    "insert into source_post "
                    "(author_account_id, corporate_entity_id, process_unit_id, "
                    " post_title, post_body, voc_type_code, visibility_code, created_at) "
                    "values (%s, %s, %s, %s, 'body', 'voc', 'public', %s) returning post_id",
                    (author_id, corp_id, process_unit_id, f"high week3 report post {idx}", created_w03),
                )
                post_id = cur.fetchone()[0]
                for code in CRITERION_CODES:
                    cur.execute(
                        "insert into post_evaluation_response "
                        "(post_id, criterion_code, rubric_version, response_category) "
                        "values (%s, %s, '2026-08-13', %s)",
                        (post_id, code, IRT_CATEGORY_COUNT - 1),
                    )
    finally:
        admin_conn.close()

    rebuild_w03 = client.post(
        "/api/reports/process_unit/2026-W03/rebuild",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert rebuild_w03.status_code == 200, rebuild_w03.text
    week3 = client.get(
        "/api/reports/process_unit/2026-W03",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert week3.status_code == 200, week3.text
    linked = week3.json()["reports"]
    assert linked
    assert linked[0]["link_method"] == "fipc"
    assert linked[0]["anchor_period_code"] == "2026-W02"
    assert linked[0]["mean_theta"] > reports[0]["mean_theta"]


def test_shared_metric_ranks_two_process_units(client, demo_analyst_token, seeded_db) -> None:
    """Two process units in one week must stay comparable on one bank.

    Independent per-unit refits would both recenter near 0. Rebuild
    scores them on the shared metric so the high unit outranks the low
    unit.
    """
    from datetime import datetime, timezone

    from lineageweave.post_evaluation import CRITERION_CODES, IRT_CATEGORY_COUNT

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
                "('permission', 'post_admin', 'Administer posts') on conflict (lookup_code) do nothing"
            )
            cur.execute("select access_role_id from account_role_assignment limit 1")
            role_id = cur.fetchone()[0]
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_admin') "
                "on conflict do nothing",
                (role_id,),
            )
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            created = datetime(2026, 1, 5, tzinfo=timezone.utc)
            for band, category in (("high", IRT_CATEGORY_COUNT - 1), ("low", 0)):
                cur.execute(
                    "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                    "values (%s, %s, %s) returning process_unit_id",
                    (corp_id, f"TEST-PU-{band.upper()}", f"{band} unit"),
                )
                unit_id = cur.fetchone()[0]
                for idx in range(4):
                    cur.execute(
                        "insert into source_post "
                        "(author_account_id, corporate_entity_id, process_unit_id, "
                        " post_title, post_body, voc_type_code, visibility_code, created_at) "
                        "values (%s, %s, %s, %s, 'body', 'voc', 'public', %s) returning post_id",
                        (author_id, corp_id, unit_id, f"{band} unit post {idx}", created),
                    )
                    post_id = cur.fetchone()[0]
                    for code in CRITERION_CODES:
                        cur.execute(
                            "insert into post_evaluation_response "
                            "(post_id, criterion_code, rubric_version, response_category) "
                            "values (%s, %s, '2026-08-13', %s)",
                            (post_id, code, category),
                        )
    finally:
        admin_conn.close()

    rebuild = client.post(
        "/api/reports/process_unit/2026-W02/rebuild",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["group_count"] >= 2

    response = client.get(
        "/api/reports/process_unit/2026-W02",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )
    assert response.status_code == 200, response.text
    reports = response.json()["reports"]
    high_report = next(
        report for report in reports if any(m["post_title"].startswith("high unit") for m in report["members"])
    )
    low_report = next(
        report for report in reports if any(m["post_title"].startswith("low unit") for m in report["members"])
    )
    assert high_report["mean_theta"] > low_report["mean_theta"]
    assert high_report["link_method"] == "fipc"
    assert low_report["link_method"] == "fipc"
    for report in (high_report, low_report):
        selected = report["selected_items"]
        assert [item["rank"] for item in selected] == [1, 2, 3]
        assert all(item["information"] > 0.0 for item in selected)
        assert {item["item_code"] for item in selected} == set(CRITERION_CODES)

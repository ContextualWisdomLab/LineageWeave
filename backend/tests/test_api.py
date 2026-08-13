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

from lineageweave.http_client import HttpClientError, get_json, post_form

_POSTGRES_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
_KEYCLOAK_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL", "http://localhost:18080")
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


pytestmark = pytest.mark.skipif(
    not (_postgres_available() and _keycloak_available()),
    reason="requires both a reachable local PostgreSQL and Keycloak -- run `make up` first",
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
                "('entity_relationship_type', 'rel_vos', 'Voice of Supplier')"
            )
            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('TEST-CORP', 'Test Corp', 'group') returning corporate_entity_id"
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

            def _insert_post(title: str, corporate_entity_id, visibility_code: str) -> str:
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'body', 'voc', %s) returning post_id",
                    (account_id, corporate_entity_id, title, visibility_code),
                )
                return str(cur.fetchone()[0])

            public_post_id = _insert_post("Public post", other_corp_id, "public")
            own_private_post_id = _insert_post("Own-corp private post", own_corp_id, "private")
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


def test_own_corp_private_post_detail_is_readable(client, demo_analyst_token, seeded_db) -> None:
    response = client.get(
        f"/api/posts/{seeded_db['own_private_post_id']}", headers={"Authorization": f"Bearer {demo_analyst_token}"}
    )
    assert response.status_code == 200
    assert response.json()["post_body"] == "body"


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
    assert names["Priya Nair"]["person_side_code"] == "counterparty"
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

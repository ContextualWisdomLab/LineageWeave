"""Real-integration test for the FastAPI backend: a genuine access token
from a live Keycloak, verified against Keycloak's live JWKS, against a
throwaway PostgreSQL database migrated with the actual schema file --
proving the OIDC + RBAC + ABAC path actually enforces what it claims to,
not just that the code type-checks.

Skipped unless both a local PostgreSQL server and a local Keycloak
(`docker compose up`, matching this repo's default ports) are reachable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import jwt
import psycopg2
import pytest

_POSTGRES_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
_KEYCLOAK_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL", "http://localhost:18080")
_REALM = "lineageweave-demo"
_MIGRATION_PATH = Path(__file__).resolve().parents[2] / "migrations" / "0001_initial_schema.sql"


def _postgres_available() -> bool:
    try:
        psycopg2.connect(_POSTGRES_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


def _keycloak_available() -> bool:
    try:
        url = f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}/.well-known/openid-configuration"
        with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310 -- local dev Keycloak
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not (_postgres_available() and _keycloak_available()),
    reason="requires both a reachable local PostgreSQL and Keycloak -- run `make up` first",
)


def _fetch_demo_analyst_token() -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "lineageweave-frontend",
            "username": "demo.analyst",
            "password": "lineageweave-demo-only",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{_KEYCLOAK_BASE_URL}/realms/{_REALM}/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))["access_token"]


@pytest.fixture(scope="module")
def demo_analyst_token() -> str:
    return _fetch_demo_analyst_token()


@pytest.fixture
def seeded_db(demo_analyst_token):
    """A throwaway, freshly migrated database seeded with a user_account
    keyed to the real Keycloak demo.analyst subject, plus three posts
    covering the three visibility outcomes the API must distinguish:
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
                "('permission', 'post_read', 'Read posts')"
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
                    "insert into post (author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'body', 'voc', %s) returning post_id",
                    (account_id, corporate_entity_id, title, visibility_code),
                )
                return str(cur.fetchone()[0])

            public_post_id = _insert_post("Public post", other_corp_id, "public")
            own_private_post_id = _insert_post("Own-corp private post", own_corp_id, "private")
            other_private_post_id = _insert_post("Other-corp private post", other_corp_id, "private")
        conn.commit()

        yield {
            "dsn": db_dsn,
            "public_post_id": public_post_id,
            "own_private_post_id": own_private_post_id,
            "other_private_post_id": other_private_post_id,
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

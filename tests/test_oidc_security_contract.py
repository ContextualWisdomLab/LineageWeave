"""Static security contracts for the repository-owned demo OIDC fixture."""

from __future__ import annotations

import json
import re
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_REALM_EXPORT = _REPOSITORY_ROOT / "docker" / "keycloak" / "realm-export.json"
_KEYCLOAK_DOCKERFILE = _REPOSITORY_ROOT / "docker" / "keycloak" / "Dockerfile"
_SMOKE_SCRIPT = _REPOSITORY_ROOT / "scripts" / "smoke_test_oidc.py"
_BACKEND_AUTH = _REPOSITORY_ROOT / "backend" / "app" / "auth.py"
_AUTOMATION_SUBJECT_ID = "33333333-3333-4333-8333-333333333333"
_ADMIN_TEST_SUBJECT_ID = "44444444-4444-4444-8444-444444444444"
_ROPC_ASSIGNMENT = re.compile(
    r'''(?x)(?:["']grant_type["']|grant_type)\s*:\s*["']password["']'''
)
_ROPC_ACTOR_ROOTS = (
    _REPOSITORY_ROOT / "scripts",
    _REPOSITORY_ROOT / "backend" / "tests",
)
_ROPC_ACTOR_SUFFIXES = {".js", ".py", ".sh", ".ts"}


def _realm() -> dict[str, object]:
    return json.loads(_REALM_EXPORT.read_text(encoding="utf-8"))


def _client(client_id: str) -> dict[str, object]:
    realm = _realm()
    matching = [client for client in realm["clients"] if client.get("clientId") == client_id]
    assert len(matching) == 1, f"expected exactly one {client_id!r} client, got {len(matching)}"
    return matching[0]


def _user(username: str) -> dict[str, object]:
    realm = _realm()
    matching = [user for user in realm["users"] if user.get("username") == username]
    assert len(matching) == 1, f"expected exactly one {username!r} user, got {len(matching)}"
    return matching[0]


def _custom_audiences(client: dict[str, object]) -> set[str]:
    mappers = client.get("protocolMappers")
    assert isinstance(mappers, list)
    audiences: set[str] = set()
    for mapper in mappers:
        if not isinstance(mapper, dict) or mapper.get("protocolMapper") != "oidc-audience-mapper":
            continue
        config = mapper.get("config")
        if isinstance(config, dict):
            audience = config.get("included.custom.audience")
            if isinstance(audience, str) and audience:
                audiences.add(audience)
    return audiences


def test_keycloak_image_uses_startup_import_realm_filename() -> None:
    """Keycloak startup import requires the realm-name file convention."""
    dockerfile = _KEYCLOAK_DOCKERFILE.read_text(encoding="utf-8")

    assert (
        "COPY realm-export.json /opt/keycloak/data/import/lineageweave-demo-realm.json"
        in dockerfile
    )
    assert "/opt/keycloak/data/import/realm-export.json" not in dockerfile


def test_machine_smoke_and_backend_share_one_jwks_key_selector() -> None:
    """Operator evidence must not drift to a weaker JWT/JWK acceptance path."""
    smoke = _SMOKE_SCRIPT.read_text(encoding="utf-8")
    backend_auth = _BACKEND_AUTH.read_text(encoding="utf-8")
    assert "select_rs256_signing_key" in smoke
    assert "select_rs256_signing_key" in backend_auth
    assert "def _signing_key_from_jwks" not in smoke
    assert "RSAAlgorithm" not in smoke


def test_repository_owned_auth_actors_do_not_use_password_grants() -> None:
    """Disable ROPC only after every owned executable auth actor stops consuming it."""
    offenders: list[str] = []
    for root in _ROPC_ACTOR_ROOTS:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in _ROPC_ACTOR_SUFFIXES:
                continue
            if _ROPC_ASSIGNMENT.search(path.read_text(encoding="utf-8")):
                offenders.append(path.relative_to(_REPOSITORY_ROOT).as_posix())

    assert offenders == [], f"repository auth actors still use grant_type=password: {sorted(offenders)}"


def test_public_frontend_uses_redirect_flow_without_direct_access_grants() -> None:
    """The browser client must require the redirect flow without password or implicit grants."""
    frontend = _client("lineageweave-frontend")

    assert frontend["publicClient"] is True
    assert frontend["standardFlowEnabled"] is True
    assert frontend["implicitFlowEnabled"] is False
    assert frontend["directAccessGrantsEnabled"] is False
    assert frontend["serviceAccountsEnabled"] is False


def test_public_frontend_requires_s256_pkce() -> None:
    """A public browser client must make PKCE S256 mandatory, not optional."""
    frontend = _client("lineageweave-frontend")
    attributes = frontend.get("attributes")

    assert isinstance(attributes, dict)
    assert attributes.get("pkce.code.challenge.method") == "S256"


def test_automation_client_is_machine_only_and_resource_scoped() -> None:
    """Non-browser harnesses use a separate confidential service account."""
    automation = _client("lineageweave-test-automation")

    assert automation["publicClient"] is False
    assert automation["standardFlowEnabled"] is False
    assert automation["implicitFlowEnabled"] is False
    assert automation["directAccessGrantsEnabled"] is False
    assert automation["serviceAccountsEnabled"] is True
    assert automation["secret"] == "${KEYCLOAK_CLIENT_SECRET}"
    assert _custom_audiences(automation) == {
        "lineageweave-api",
        "http://localhost:18001/mcp",
    }


def test_automation_service_account_subject_is_deterministic() -> None:
    """Local authorization can provision the machine principal without Admin REST discovery."""
    automation_user = _user("service-account-lineageweave-test-automation")

    assert automation_user["id"] == _AUTOMATION_SUBJECT_ID
    assert automation_user["serviceAccountClientId"] == "lineageweave-test-automation"
    assert automation_user.get("credentials", []) == []


def test_admin_integration_client_is_api_only_and_machine_only() -> None:
    """Cross-account API denial uses a distinct confidential admin test actor."""
    admin = _client("lineageweave-test-admin")

    assert admin["publicClient"] is False
    assert admin["standardFlowEnabled"] is False
    assert admin["implicitFlowEnabled"] is False
    assert admin["directAccessGrantsEnabled"] is False
    assert admin["serviceAccountsEnabled"] is True
    assert admin["secret"] == "${KEYCLOAK_TEST_ADMIN_CLIENT_SECRET}"
    assert _custom_audiences(admin) == {"lineageweave-api"}


def test_admin_integration_service_account_subject_is_deterministic() -> None:
    """The negative authorization proof must keep an exact subject distinct from automation."""
    admin_user = _user("service-account-lineageweave-test-admin")

    assert admin_user["id"] == _ADMIN_TEST_SUBJECT_ID
    assert admin_user["id"] != _AUTOMATION_SUBJECT_ID
    assert admin_user["serviceAccountClientId"] == "lineageweave-test-admin"
    assert admin_user.get("credentials", []) == []

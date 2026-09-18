"""Static security contracts for the repository-owned demo OIDC fixture."""

from __future__ import annotations

import json
import re
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_REALM_EXPORT = _REPOSITORY_ROOT / "docker" / "keycloak" / "realm-export.json"
_KEYCLOAK_DOCKERFILE = _REPOSITORY_ROOT / "docker" / "keycloak" / "Dockerfile"
_SMOKE_SCRIPT = _REPOSITORY_ROOT / "scripts" / "smoke_test_oidc.py"
_ROPC_ASSIGNMENT = re.compile(
    r'''(?x)(?:["']grant_type["']|grant_type)\s*:\s*["']password["']'''
)
_ROPC_ACTOR_ROOTS = (
    _REPOSITORY_ROOT / "scripts",
    _REPOSITORY_ROOT / "backend" / "tests",
)
_ROPC_ACTOR_SUFFIXES = {".js", ".py", ".sh", ".ts"}


def _client(client_id: str) -> dict[str, object]:
    realm = json.loads(_REALM_EXPORT.read_text(encoding="utf-8"))
    matching = [client for client in realm["clients"] if client.get("clientId") == client_id]
    assert len(matching) == 1, f"expected exactly one {client_id!r} client, got {len(matching)}"
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


def test_machine_smoke_reuses_the_product_jwks_key_selector() -> None:
    """Operator evidence must not drift to a weaker JWT/JWK acceptance path."""
    smoke = _SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "from backend.app.auth import _signing_key_from_jwks" in smoke
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
    """The browser client must require the redirect flow without password grants."""
    frontend = _client("lineageweave-frontend")

    assert frontend["publicClient"] is True
    assert frontend["standardFlowEnabled"] is True
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
    assert automation["directAccessGrantsEnabled"] is False
    assert automation["serviceAccountsEnabled"] is True
    assert _custom_audiences(automation) == {
        "lineageweave-api",
        "http://localhost:18001/mcp",
    }

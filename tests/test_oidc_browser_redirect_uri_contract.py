"""Security contract for the local browser OIDC redirect registration."""

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_REALM_EXPORT = _REPO_ROOT / "docker" / "keycloak" / "realm-export.json"
_FRONTEND_MAIN = _REPO_ROOT / "frontend" / "src" / "main.tsx"


def _frontend_client() -> dict[str, object]:
    realm = json.loads(_REALM_EXPORT.read_text())
    clients = [
        client
        for client in realm["clients"]
        if client.get("clientId") == "lineageweave-frontend"
    ]
    assert len(clients) == 1
    return clients[0]


def test_browser_redirect_uris_exactly_match_the_two_local_app_origins() -> None:
    """Do not widen the authorization-code callback with wildcard path matching."""
    client = _frontend_client()

    assert client["redirectUris"] == [
        "http://localhost:5173",
        "http://localhost:15173",
    ]
    assert all("*" not in uri for uri in client["redirectUris"])


def test_browser_runtime_uses_the_registered_origin_as_redirect_uri() -> None:
    """The SPA redirect must stay equal to the exact URI registered in Keycloak."""
    source = _FRONTEND_MAIN.read_text()

    assert "redirect_uri: window.location.origin" in source
    assert "post_logout_redirect_uri: window.location.origin" in source


def test_browser_client_keeps_code_pkce_and_disables_implicit_flow() -> None:
    """Exact redirect matching is part of the existing Authorization Code + PKCE contract."""
    client = _frontend_client()

    assert client["publicClient"] is True
    assert client["standardFlowEnabled"] is True
    assert client["implicitFlowEnabled"] is False
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"

"""Source contracts for the local backend integration OAuth actors.

The backend integration suite is a machine consumer. It must exercise the
same API authorization boundary without asking the public SPA client for
resource-owner password grants. Human browser login remains covered by the
Authorization Code + PKCE product path.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INTEGRATION = ROOT / "backend" / "tests" / "test_api.py"
MACHINE_OAUTH_SUPPORT = ROOT / "backend" / "tests" / "integration_oauth_support.py"
REALM_EXPORT = ROOT / "docker" / "keycloak" / "realm-export.json"


def _realm_client(client_id: str) -> dict[str, object]:
    realm = json.loads(REALM_EXPORT.read_text())
    matches = [
        client
        for client in realm.get("clients", [])
        if isinstance(client, dict) and client.get("clientId") == client_id
    ]
    assert len(matches) == 1, f"expected exactly one realm client {client_id!r}"
    return matches[0]


def test_backend_integration_uses_distinct_confidential_machine_actors() -> None:
    integration_source = BACKEND_INTEGRATION.read_text()
    support_source = MACHINE_OAUTH_SUPPORT.read_text()

    assert '"grant_type": "password"' not in integration_source
    assert '"username": "demo.analyst"' not in integration_source
    assert '"username": "demo.admin"' not in integration_source
    assert '"client_id": "lineageweave-frontend"' not in integration_source

    assert '"grant_type": "client_credentials"' in support_source
    assert '"lineageweave-test-automation"' in support_source
    assert '"lineageweave-test-admin"' in support_source
    assert "KEYCLOAK_CLIENT_SECRET" in support_source
    assert "KEYCLOAK_TEST_ADMIN_CLIENT_SECRET" in support_source
    assert "fetch_viewer_machine_token" in integration_source
    assert "fetch_admin_machine_token" in integration_source


def test_public_browser_client_disables_direct_access_grants_after_migration() -> None:
    frontend = _realm_client("lineageweave-frontend")
    assert frontend.get("publicClient") is True
    assert frontend.get("standardFlowEnabled") is True
    assert frontend.get("implicitFlowEnabled") is False
    assert frontend.get("directAccessGrantsEnabled") is False
    assert frontend.get("attributes", {}).get("pkce.code.challenge.method") == "S256"


def test_machine_clients_cannot_fall_back_to_human_flows() -> None:
    for client_id in ("lineageweave-test-automation", "lineageweave-test-admin"):
        client = _realm_client(client_id)
        assert client.get("publicClient") is False
        assert client.get("serviceAccountsEnabled") is True
        assert client.get("standardFlowEnabled") is False
        assert client.get("implicitFlowEnabled") is False
        assert client.get("directAccessGrantsEnabled") is False

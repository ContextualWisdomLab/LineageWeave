"""Static security contracts for the repository-owned demo OIDC fixture."""

from __future__ import annotations

import json
from pathlib import Path


_REALM_EXPORT = (
    Path(__file__).resolve().parents[1] / "docker" / "keycloak" / "realm-export.json"
)


def _client(client_id: str) -> dict[str, object]:
    realm = json.loads(_REALM_EXPORT.read_text(encoding="utf-8"))
    matching = [client for client in realm["clients"] if client.get("clientId") == client_id]
    assert len(matching) == 1, f"expected exactly one {client_id!r} client, got {len(matching)}"
    return matching[0]


def test_public_frontend_uses_redirect_flow_without_direct_access_grants() -> None:
    """The browser client must not expose the OAuth password grant."""
    frontend = _client("lineageweave-frontend")

    assert frontend["publicClient"] is True
    assert frontend["standardFlowEnabled"] is True
    assert frontend["directAccessGrantsEnabled"] is False
    assert frontend["serviceAccountsEnabled"] is False

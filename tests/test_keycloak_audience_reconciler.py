from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from backend.app import keycloak_audience_reconciler as reconciler


ROOT = Path(__file__).resolve().parents[1]
OLD_AUDIENCE = "http://localhost:18001/mcp"
NEW_AUDIENCE = "http://localhost:19001/mcp"


def _settings(audience: str = NEW_AUDIENCE) -> reconciler.KeycloakAudienceSettings:
    """Return deterministic local-demo reconciliation settings."""
    return reconciler.KeycloakAudienceSettings(
        base_url="http://keycloak:8080",
        admin_username="admin",
        admin_password="secret",
        target_realm="lineageweave-demo",
        target_client_id="lineageweave-frontend",
        mapper_name="lineageweave-mcp-audience",
        audience=audience,
        maximum_attempts=3,
        retry_delay_seconds=0,
        timeout_seconds=2,
    )


class _KeycloakState:
    """Stateful Admin REST transport for an existing persistent realm."""

    def __init__(self, *, mapper: dict[str, Any] | None) -> None:
        self.mapper = mapper
        self.put_count = 0
        self.post_count = 0
        self.authorization_headers: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/realms/master/protocol/openid-connect/token":
            return httpx.Response(200, json={"access_token": "admin-token"})
        authorization = request.headers.get("authorization", "")
        self.authorization_headers.append(authorization)
        if request.url.path == "/admin/realms/lineageweave-demo/clients":
            assert request.url.params.get("clientId") == "lineageweave-frontend"
            return httpx.Response(
                200,
                json=[{"id": "client-uuid", "clientId": "lineageweave-frontend"}],
            )
        mapper_collection = (
            "/admin/realms/lineageweave-demo/clients/client-uuid/"
            "protocol-mappers/models"
        )
        if request.url.path == mapper_collection and request.method == "GET":
            return httpx.Response(200, json=[] if self.mapper is None else [self.mapper])
        if request.url.path == mapper_collection and request.method == "POST":
            self.post_count += 1
            payload = json.loads(request.content)
            self.mapper = {"id": "new-mapper-uuid", **payload}
            return httpx.Response(201)
        if (
            request.url.path == f"{mapper_collection}/mapper-uuid"
            and request.method == "PUT"
        ):
            self.put_count += 1
            self.mapper = json.loads(request.content)
            return httpx.Response(204)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")


def _client(state: _KeycloakState) -> httpx.Client:
    return httpx.Client(
        base_url="http://keycloak:8080",
        transport=httpx.MockTransport(state.handler),
    )


def test_reconcile_updates_persistent_mapper_after_port_change_and_is_idempotent() -> None:
    """A redeploy from port 18001 to 19001 updates the existing realm mapper once."""
    state = _KeycloakState(
        mapper={
            "id": "mapper-uuid",
            "name": "lineageweave-mcp-audience",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "config": {
                "included.custom.audience": OLD_AUDIENCE,
                "access.token.claim": "true",
                "id.token.claim": "false",
            },
        }
    )
    with _client(state) as client:
        assert reconciler.reconcile_mcp_audience(_settings(), client=client) is True
        assert reconciler.reconcile_mcp_audience(_settings(), client=client) is False

    assert state.put_count == 1
    assert state.post_count == 0
    assert state.mapper is not None
    assert state.mapper["config"]["included.custom.audience"] == NEW_AUDIENCE
    assert set(state.authorization_headers) == {"Bearer admin-token"}


def test_reconcile_creates_missing_mapper_without_replacing_the_realm() -> None:
    """An older persistent realm gains only the missing dedicated audience mapper."""
    state = _KeycloakState(mapper=None)
    with _client(state) as client:
        assert reconciler.reconcile_mcp_audience(_settings(), client=client) is True

    assert state.put_count == 0
    assert state.post_count == 1
    assert state.mapper is not None
    assert state.mapper["name"] == "lineageweave-mcp-audience"
    assert state.mapper["protocolMapper"] == "oidc-audience-mapper"
    assert state.mapper["config"]["included.custom.audience"] == NEW_AUDIENCE


def test_reconcile_rejects_unsafe_or_conflicting_mapper_contracts() -> None:
    """Unsafe audience URLs and same-name mapper type drift fail closed."""
    with pytest.raises(ValueError, match="audience"):
        reconciler.KeycloakAudienceSettings(
            **{
                **_settings().__dict__,
                "audience": "http://user:secret@localhost:19001/mcp?leak=true",
            }
        ).validate()

    state = _KeycloakState(
        mapper={
            "id": "mapper-uuid",
            "name": "lineageweave-mcp-audience",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-hardcoded-claim-mapper",
            "config": {},
        }
    )
    with _client(state) as client:
        with pytest.raises(reconciler.KeycloakAudienceReconciliationError, match="mapper type"):
            reconciler.reconcile_mcp_audience(_settings(), client=client)
    assert state.put_count == 0


def test_compose_completes_reconciliation_before_starting_mcp() -> None:
    """The MCP process waits for the idempotent Admin REST reconciliation slice."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  keycloak_mcp_audience:\n" in compose
    reconciler_section = compose.split("\n  keycloak_mcp_audience:\n", 1)[1].split(
        "\n  backend:\n", 1
    )[0]
    assert "backend.app.keycloak_audience_reconciler" in reconciler_section
    assert "MCP_AUDIENCE: http://localhost:${MCP_PORT:-18001}/mcp" in reconciler_section
    mcp_section = compose.split("\n  mcp:\n", 1)[1].split("\n  frontend:\n", 1)[0]
    assert "keycloak_mcp_audience:" in mcp_section
    assert "condition: service_completed_successfully" in mcp_section

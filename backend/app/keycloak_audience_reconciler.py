"""Idempotently align the persistent Keycloak MCP audience mapper.

Startup realm import intentionally skips an already-existing realm. This module
uses the Keycloak Admin REST API to reconcile only the dedicated audience mapper,
so changing ``MCP_AUDIENCE`` does not require deleting the realm database or
re-importing unrelated identity configuration.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote, urlsplit

import httpx

_MAPPER_PROTOCOL = "openid-connect"
_MAPPER_TYPE = "oidc-audience-mapper"
_RETRYABLE_STATUS_CODES = frozenset({404, 409, 425, 429, 502, 503, 504})


class KeycloakAudienceReconciliationError(RuntimeError):
    """The dedicated MCP audience mapper could not be reconciled safely."""


@dataclass(frozen=True)
class KeycloakAudienceSettings:
    """Configuration for one bounded Keycloak audience reconciliation run."""

    base_url: str
    admin_username: str
    admin_password: str
    target_realm: str
    target_client_id: str
    mapper_name: str
    audience: str
    maximum_attempts: int = 60
    retry_delay_seconds: float = 2.0
    timeout_seconds: float = 5.0

    def validate(self) -> None:
        """Fail closed on missing credentials, unsafe URLs, or invalid bounds."""
        for name, value in (
            ("base_url", self.base_url),
            ("admin_username", self.admin_username),
            ("admin_password", self.admin_password),
            ("target_realm", self.target_realm),
            ("target_client_id", self.target_client_id),
            ("mapper_name", self.mapper_name),
            ("audience", self.audience),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")
        _validate_url(self.base_url, name="base_url", allow_path=False)
        _validate_url(self.audience, name="audience", allow_path=True)
        if self.maximum_attempts < 1 or self.maximum_attempts > 300:
            raise ValueError("maximum_attempts must be between 1 and 300")
        if self.retry_delay_seconds < 0 or self.retry_delay_seconds > 30:
            raise ValueError("retry_delay_seconds must be between 0 and 30")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 60:
            raise ValueError("timeout_seconds must be greater than 0 and at most 60")


def _validate_url(value: str, *, name: str, allow_path: bool) -> None:
    """Require a credential-free HTTP(S) endpoint without query or fragment."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{name} must not contain a query or fragment")
    if not allow_path and parsed.path not in {"", "/"}:
        raise ValueError(f"{name} must not contain a path")


def load_settings() -> KeycloakAudienceSettings:
    """Load the reconciler contract from environment variables."""
    settings = KeycloakAudienceSettings(
        base_url=os.environ.get("KEYCLOAK_ADMIN_BASE_URL", "http://keycloak:8080"),
        admin_username=os.environ.get(
            "KEYCLOAK_ADMIN_USERNAME",
            os.environ.get("KEYCLOAK_ADMIN", "admin"),
        ),
        admin_password=os.environ.get(
            "KEYCLOAK_ADMIN_PASSWORD",
            os.environ.get("KC_BOOTSTRAP_ADMIN_PASSWORD", ""),
        ),
        target_realm=os.environ.get("KEYCLOAK_TARGET_REALM", "lineageweave-demo"),
        target_client_id=os.environ.get(
            "KEYCLOAK_TARGET_CLIENT_ID", "lineageweave-frontend"
        ),
        mapper_name=os.environ.get(
            "KEYCLOAK_MCP_MAPPER_NAME", "lineageweave-mcp-audience"
        ),
        audience=os.environ.get("MCP_AUDIENCE", "http://localhost:18001/mcp"),
        maximum_attempts=int(os.environ.get("KEYCLOAK_RECONCILE_MAX_ATTEMPTS", "60")),
        retry_delay_seconds=float(
            os.environ.get("KEYCLOAK_RECONCILE_RETRY_SECONDS", "2")
        ),
        timeout_seconds=float(os.environ.get("KEYCLOAK_RECONCILE_TIMEOUT_SECONDS", "5")),
    )
    settings.validate()
    return settings


def _json_payload(response: httpx.Response, *, operation: str) -> Any:
    """Raise on HTTP or JSON contract failures without echoing response bodies."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise KeycloakAudienceReconciliationError(
            f"Keycloak {operation} failed with HTTP {response.status_code}"
        ) from exc
    try:
        return response.json()
    except ValueError as exc:
        raise KeycloakAudienceReconciliationError(
            f"Keycloak {operation} returned invalid JSON"
        ) from exc


def _admin_token(client: httpx.Client, settings: KeycloakAudienceSettings) -> str:
    """Obtain a short-lived admin token without retaining or logging credentials."""
    response = client.post(
        "/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    payload = _json_payload(response, operation="admin authentication")
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise KeycloakAudienceReconciliationError(
            "Keycloak admin authentication returned no access token"
        )
    token = payload["access_token"].strip()
    if not token:
        raise KeycloakAudienceReconciliationError(
            "Keycloak admin authentication returned an empty access token"
        )
    return token


def _find_client(
    client: httpx.Client,
    settings: KeycloakAudienceSettings,
    headers: dict[str, str],
) -> str:
    """Resolve exactly one target client UUID from its stable client ID."""
    realm = quote(settings.target_realm, safe="")
    response = client.get(
        f"/admin/realms/{realm}/clients",
        params={"clientId": settings.target_client_id},
        headers=headers,
    )
    payload = _json_payload(response, operation="client lookup")
    if not isinstance(payload, list):
        raise KeycloakAudienceReconciliationError(
            "Keycloak client lookup returned a non-array payload"
        )
    exact = [
        item
        for item in payload
        if isinstance(item, dict)
        and item.get("clientId") == settings.target_client_id
        and isinstance(item.get("id"), str)
        and item["id"]
    ]
    if len(exact) != 1:
        raise KeycloakAudienceReconciliationError(
            "expected exactly one Keycloak target client"
        )
    return str(exact[0]["id"])


def _mapper_collection_path(settings: KeycloakAudienceSettings, client_uuid: str) -> str:
    realm = quote(settings.target_realm, safe="")
    client_id = quote(client_uuid, safe="")
    return f"/admin/realms/{realm}/clients/{client_id}/protocol-mappers/models"


def _mapper_payload(settings: KeycloakAudienceSettings) -> dict[str, Any]:
    """Return the minimal OIDC audience mapper owned by LineageWeave."""
    return {
        "name": settings.mapper_name,
        "protocol": _MAPPER_PROTOCOL,
        "protocolMapper": _MAPPER_TYPE,
        "config": {
            "included.custom.audience": settings.audience,
            "id.token.claim": "false",
            "access.token.claim": "true",
            "lightweight.claim": "false",
        },
    }


def reconcile_mcp_audience(
    settings: KeycloakAudienceSettings,
    *,
    client: httpx.Client | None = None,
) -> bool:
    """Create or update only the dedicated mapper; return whether state changed."""
    settings.validate()
    owns_client = client is None
    resolved_client = client or httpx.Client(
        base_url=settings.base_url.rstrip("/") + "/",
        timeout=settings.timeout_seconds,
    )
    try:
        token = _admin_token(resolved_client, settings)
        headers = {"Authorization": f"Bearer {token}"}
        client_uuid = _find_client(resolved_client, settings, headers)
        collection_path = _mapper_collection_path(settings, client_uuid)
        response = resolved_client.get(collection_path, headers=headers)
        payload = _json_payload(response, operation="protocol mapper lookup")
        if not isinstance(payload, list):
            raise KeycloakAudienceReconciliationError(
                "Keycloak protocol mapper lookup returned a non-array payload"
            )
        matches = [
            item
            for item in payload
            if isinstance(item, dict) and item.get("name") == settings.mapper_name
        ]
        if len(matches) > 1:
            raise KeycloakAudienceReconciliationError(
                "multiple Keycloak MCP audience mappers share the configured name"
            )
        if not matches:
            create_response = resolved_client.post(
                collection_path,
                headers=headers,
                json=_mapper_payload(settings),
            )
            try:
                create_response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise KeycloakAudienceReconciliationError(
                    f"Keycloak protocol mapper creation failed with HTTP "
                    f"{create_response.status_code}"
                ) from exc
            return True

        mapper = matches[0]
        if (
            mapper.get("protocol") != _MAPPER_PROTOCOL
            or mapper.get("protocolMapper") != _MAPPER_TYPE
        ):
            raise KeycloakAudienceReconciliationError(
                "existing Keycloak MCP mapper type conflicts with the required audience mapper type"
            )
        mapper_id = mapper.get("id")
        if not isinstance(mapper_id, str) or not mapper_id:
            raise KeycloakAudienceReconciliationError(
                "existing Keycloak MCP audience mapper has no stable id"
            )
        config = mapper.get("config")
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise KeycloakAudienceReconciliationError(
                "existing Keycloak MCP audience mapper config is not an object"
            )
        desired_config = {
            **config,
            "included.custom.audience": settings.audience,
            "id.token.claim": "false",
            "access.token.claim": "true",
            "lightweight.claim": "false",
        }
        if config == desired_config:
            return False
        updated_mapper = {**mapper, "config": desired_config}
        mapper_path = f"{collection_path}/{quote(mapper_id, safe='')}"
        update_response = resolved_client.put(
            mapper_path,
            headers=headers,
            json=updated_mapper,
        )
        try:
            update_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise KeycloakAudienceReconciliationError(
                f"Keycloak protocol mapper update failed with HTTP "
                f"{update_response.status_code}"
            ) from exc
        return True
    finally:
        if owns_client:
            resolved_client.close()


ClientFactory = Callable[[KeycloakAudienceSettings], httpx.Client]


def reconcile_with_retry(
    settings: KeycloakAudienceSettings,
    *,
    client_factory: ClientFactory | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Wait for Keycloak readiness, then reconcile or fail with a bounded error."""
    settings.validate()
    factory = client_factory or (
        lambda candidate: httpx.Client(
            base_url=candidate.base_url.rstrip("/") + "/",
            timeout=candidate.timeout_seconds,
        )
    )
    last_error: Exception | None = None
    for attempt in range(1, settings.maximum_attempts + 1):
        try:
            with factory(settings) as client:
                return reconcile_mcp_audience(settings, client=client)
        except httpx.RequestError as exc:
            last_error = exc
        except KeycloakAudienceReconciliationError as exc:
            cause = exc.__cause__
            if not (
                isinstance(cause, httpx.HTTPStatusError)
                and cause.response.status_code in _RETRYABLE_STATUS_CODES
            ):
                raise
            last_error = exc
        if attempt < settings.maximum_attempts:
            sleep(settings.retry_delay_seconds)
    raise KeycloakAudienceReconciliationError(
        "Keycloak did not become ready for MCP audience reconciliation within the configured attempts"
    ) from last_error


def main() -> int:
    """Run the bounded startup reconciliation without printing secrets or tokens."""
    changed = reconcile_with_retry(load_settings())
    state = "updated" if changed else "already current"
    print(f"Keycloak MCP audience mapper is {state}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Environment-driven settings. No file-based config, no defaults that
silently point at a real deployment -- every value is either a genuinely
safe local-dev default or must be set explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _csv_setting(name: str, default: str = "") -> list[str]:
    """Return one comma-separated setting as stripped, non-empty values."""
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


def _bounded_int_setting(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Read one base-10 integer and fail closed outside its configured bounds."""
    raw_value = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw_value, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a base-10 integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _home_dotenv_values(names: set[str]) -> dict[str, str]:
    """Read only requested non-secret setting names from ``~/.env``."""
    try:
        lines = (Path.home() / ".env").read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, raw_value = line.partition("=")
        if not separator or key.strip() not in names:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _gateway_setting(*names: str) -> str:
    """Resolve process env first, then the user's home dotenv file."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    dotenv = _home_dotenv_values(set(names))
    return next((dotenv[name].strip() for name in names if dotenv.get(name, "").strip()), "")


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by the REST API and MCP resource server."""

    database_url: str
    # Reachable *from this backend process* -- used only to fetch JWKS
    # signing keys. Inside docker-compose this is the internal service DNS
    # name (http://keycloak:8080); JWKS content is the same regardless of
    # which hostname reaches it.
    keycloak_base_url: str
    keycloak_realm: str
    keycloak_client_id: str
    # The issuer string real tokens actually carry -- whatever hostname the
    # browser/client used to log in (Keycloak's hostname-strict=false mode
    # reflects the request's Host header into the `iss` claim). This is
    # deliberately a *separate* setting from keycloak_base_url: inside
    # docker-compose the two differ (internal DNS name vs. the
    # host-published port a browser actually hits).
    keycloak_issuer: str
    # Exact browser origins allowed by CORS. Comma-separated FRONTEND_ORIGINS;
    # never a wildcard -- the backend only serves the product UI.
    frontend_origins: list[str]
    # Keyman extraction is a hard dependency of POST /api/posts/{id}/extract-keymen
    # only -- every other endpoint works with these unset. Empty string, not
    # a fabricated default, when unconfigured (see keyman_ingestion.py).
    orchestrator_base_url: str
    orchestrator_api_key: str
    # Legacy compatibility field. The value is not sent to the gateway:
    # contextual-orchestrator owns vision-model discovery. The image channel
    # is unavailable only when the shared gateway credentials are absent.
    vision_model: str
    # Event queue for post/ticket activity and the distributed MCP invocation
    # limiter. A rate-limit backend outage fails closed; it never degrades to a
    # per-process counter that can be bypassed by changing replicas.
    valkey_url: str
    # Self-hosted Searxng instance relation_verification.py's real client
    # checks Knowledge Graph relation inferences against (ADR 0005). Empty
    # means the verification channel is unavailable, same "no fake
    # channel" discipline as every other pluggable client.
    searxng_base_url: str
    # Optional TEPP HTTP transport. Empty keeps TeppClient's default
    # unavailable transport. Never a local psychometric substitute.
    tepp_transport_url: str
    # RankWeave ranking port (ADR 0030). True = fail-closed
    # RankWeaveNotAvailable -- never invent a fused score. Default false
    # uses the in-process library already required by reconstruct.py.
    rankweave_disabled: bool
    # Public Streamable HTTP MCP resource URL. It is also the default JWT
    # audience, so tokens issued for the REST frontend cannot be replayed
    # unless the IdP explicitly includes this resource audience.
    mcp_resource_url: str = "http://localhost:18001/mcp"
    mcp_audience: str = "http://localhost:18001/mcp"
    # Optional OAuth scopes are enforced by the MCP SDK. Product RBAC and
    # ABAC are always enforced in addition, even when this list is empty.
    mcp_required_scopes: list[str] = field(default_factory=list)
    # Exact Host/Origin allowlists for MCP DNS-rebinding protection.
    mcp_allowed_hosts: list[str] = field(
        default_factory=lambda: ["localhost:*", "127.0.0.1:*", "mcp:8001"]
    )
    mcp_allowed_origins: list[str] = field(default_factory=list)
    # Shared fixed-window policy for authenticated Global Ask invocations.
    mcp_global_ask_rate_limit: int = 20
    mcp_global_ask_rate_window_seconds: int = 60
    # Retry metadata when the distributed limiter itself is unavailable.
    mcp_rate_limit_unavailable_retry_seconds: int = 5

    @property
    def keycloak_jwks_uri(self) -> str:
        """JWKS URL the backend process itself can reach (internal DNS in compose)."""
        return f"{self.keycloak_base_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


def load_settings() -> Settings:
    """Read Settings from the environment, with local-dev defaults only."""
    keycloak_base_url = os.environ.get("KEYCLOAK_BASE_URL", "http://localhost:18080")
    keycloak_realm = os.environ.get("KEYCLOAK_REALM", "lineageweave-demo")
    mcp_resource_url = os.environ.get("MCP_RESOURCE_URL", "http://localhost:18001/mcp")
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
        keycloak_base_url=keycloak_base_url,
        keycloak_realm=keycloak_realm,
        keycloak_client_id=os.environ.get("KEYCLOAK_CLIENT_ID", "lineageweave-frontend"),
        keycloak_issuer=os.environ.get(
            "KEYCLOAK_ISSUER", f"{keycloak_base_url}/realms/{keycloak_realm}"
        ),
        frontend_origins=_csv_setting("FRONTEND_ORIGINS", "http://localhost:5173"),
        orchestrator_base_url=_gateway_setting(
            "LLM_GATEWAY_URL", "LLM_GATEWAY_API_URL", "ORCHESTRATOR_BASE_URL"
        ),
        orchestrator_api_key=_gateway_setting("LLM_GATEWAY_API_KEY", "ORCHESTRATOR_API_KEY"),
        vision_model=os.environ.get("VISION_MODEL", ""),
        valkey_url=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
        searxng_base_url=os.environ.get("SEARXNG_BASE_URL", ""),
        tepp_transport_url=os.environ.get("TEPP_TRANSPORT_URL", ""),
        rankweave_disabled=os.environ.get("RANKWEAVE_DISABLED", "")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"},
        mcp_resource_url=mcp_resource_url,
        mcp_audience=os.environ.get("MCP_AUDIENCE", mcp_resource_url),
        mcp_required_scopes=_csv_setting("MCP_REQUIRED_SCOPES"),
        mcp_allowed_hosts=_csv_setting(
            "MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*,mcp:8001"
        ),
        mcp_allowed_origins=_csv_setting("MCP_ALLOWED_ORIGINS"),
        mcp_global_ask_rate_limit=_bounded_int_setting(
            "MCP_GLOBAL_ASK_RATE_LIMIT",
            20,
            minimum=1,
            maximum=10_000,
        ),
        mcp_global_ask_rate_window_seconds=_bounded_int_setting(
            "MCP_GLOBAL_ASK_RATE_WINDOW_SECONDS",
            60,
            minimum=1,
            maximum=86_400,
        ),
        mcp_rate_limit_unavailable_retry_seconds=_bounded_int_setting(
            "MCP_RATE_LIMIT_UNAVAILABLE_RETRY_SECONDS",
            5,
            minimum=1,
            maximum=300,
        ),
    )

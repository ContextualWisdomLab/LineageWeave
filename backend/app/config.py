"""Environment-driven settings with a runtime-only home dotenv fallback.

Only the shared orchestrator endpoint and credential aliases may fall back to
``~/.env``. Values are never copied into the repository or emitted in logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _csv_setting(name: str, default: str = "") -> list[str]:
    """Return one comma-separated setting as stripped, non-empty values."""
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


def _home_dotenv_values(names: set[str]) -> dict[str, str]:
    """Read only requested runtime setting names from the user's home dotenv."""
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
    """Resolve a gateway setting from process env, then the home dotenv."""
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
    # Production may use the organization's Keyverse OIDC issuer. The
    # keycloak fields above remain the explicit local-development fallback.
    oidc_issuer: str
    oidc_client_id: str
    # Resource audience the backend accepts. This is deliberately separate
    # from the browser OAuth client id: an access token issued for another
    # resource at the same trusted issuer must not become a LineageWeave API
    # credential merely because its signature is valid.
    oidc_audience: str
    oidc_discovery_uri: str
    oidc_jwks_uri_override: str
    oidc_clock_skew_seconds: int
    # Exact browser origins allowed by CORS. Comma-separated FRONTEND_ORIGINS;
    # never a wildcard -- the backend only serves the product UI.
    frontend_origins: list[str]
    orchestrator_base_url: str
    orchestrator_api_key: str
    embedding_model: str
    valkey_url: str
    searxng_base_url: str
    tepp_transport_url: str
    tepp_api_key: str
    caldav_base_url: str
    rankweave_disabled: bool
    mcp_resource_url: str = "http://localhost:18001/mcp"
    mcp_audience: str = "http://localhost:18001/mcp"
    mcp_required_scopes: list[str] = field(default_factory=list)
    mcp_allowed_hosts: list[str] = field(
        default_factory=lambda: ["localhost:*", "127.0.0.1:*", "mcp:8001"]
    )
    mcp_allowed_origins: list[str] = field(default_factory=list)

    @property
    def keycloak_jwks_uri(self) -> str:
        """JWKS URL the backend process itself can reach (internal DNS in compose)."""
        return f"{self.keycloak_base_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


def load_settings() -> Settings:
    """Read Settings from the environment, with local-dev defaults only."""
    keycloak_base_url = os.environ.get("KEYCLOAK_BASE_URL", "http://localhost:18080")
    keycloak_realm = os.environ.get("KEYCLOAK_REALM", "lineageweave-demo")
    keycloak_client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "lineageweave-frontend")
    keycloak_issuer = os.environ.get(
        "KEYCLOAK_ISSUER", f"{keycloak_base_url}/realms/{keycloak_realm}"
    )
    keyverse_issuer = os.environ.get("KEYVERSE_ISSUER", "").strip()
    generic_oidc_issuer = os.environ.get("OIDC_ISSUER", "").strip()
    external_oidc = bool(keyverse_issuer or generic_oidc_issuer)
    oidc_issuer = (keyverse_issuer or generic_oidc_issuer or keycloak_issuer).rstrip("/")
    oidc_client_id = (
        os.environ.get("KEYVERSE_CLIENT_ID", "").strip()
        or os.environ.get("OIDC_CLIENT_ID", "").strip()
        or keycloak_client_id
    )
    configured_audience = (
        os.environ.get("KEYVERSE_AUDIENCE", "").strip()
        or os.environ.get("OIDC_AUDIENCE", "").strip()
    )
    if external_oidc and not configured_audience:
        raise ValueError(
            "external OIDC requires KEYVERSE_AUDIENCE or OIDC_AUDIENCE; "
            "do not infer a resource-server audience from the browser client id"
        )
    oidc_audience = configured_audience or "lineageweave-api"
    oidc_discovery_uri = os.environ.get("KEYVERSE_DISCOVERY_URI", "").strip() or os.environ.get(
        "OIDC_DISCOVERY_URI", ""
    ).strip()
    if not oidc_discovery_uri:
        discovery_base = oidc_issuer if external_oidc else keycloak_base_url
        oidc_discovery_uri = (
            f"{discovery_base.rstrip('/')}/realms/{keycloak_realm}/.well-known/openid-configuration"
            if not external_oidc
            else f"{discovery_base.rstrip('/')}/.well-known/openid-configuration"
        )
    try:
        oidc_clock_skew_seconds = int(os.environ.get("OIDC_CLOCK_SKEW_SECONDS", "5"))
    except ValueError as exc:
        raise ValueError("OIDC_CLOCK_SKEW_SECONDS must be an integer") from exc
    if not 0 <= oidc_clock_skew_seconds <= 60:
        raise ValueError("OIDC_CLOCK_SKEW_SECONDS must be between 0 and 60")
    mcp_resource_url = os.environ.get("MCP_RESOURCE_URL", "http://localhost:18001/mcp")
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
        keycloak_base_url=keycloak_base_url,
        keycloak_realm=keycloak_realm,
        keycloak_client_id=keycloak_client_id,
        keycloak_issuer=keycloak_issuer,
        oidc_issuer=oidc_issuer,
        oidc_client_id=oidc_client_id,
        oidc_audience=oidc_audience,
        oidc_discovery_uri=oidc_discovery_uri,
        oidc_jwks_uri_override=(
            os.environ.get("KEYVERSE_JWKS_URI", "").strip()
            or os.environ.get("OIDC_JWKS_URI", "").strip()
            or (
                f"{keycloak_base_url}/realms/{keycloak_realm}/protocol/openid-connect/certs"
                if not external_oidc
                else ""
            )
        ),
        oidc_clock_skew_seconds=oidc_clock_skew_seconds,
        frontend_origins=_csv_setting("FRONTEND_ORIGINS", "http://localhost:5173"),
        orchestrator_base_url=_gateway_setting(
            "LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL", "ORCHESTRATOR_BASE_URL"
        ),
        orchestrator_api_key=_gateway_setting("LLM_GATEWAY_API_KEY", "ORCHESTRATOR_API_KEY"),
        embedding_model=os.environ.get("LLM_GATEWAY_EMBEDDING_MODEL", "").strip(),
        valkey_url=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
        searxng_base_url=os.environ.get("SEARXNG_BASE_URL", ""),
        tepp_transport_url=os.environ.get("TEPP_TRANSPORT_URL", ""),
        tepp_api_key=os.environ.get("TEPP_API_KEY", ""),
        caldav_base_url=os.environ.get("CALDAV_BASE_URL", "").strip(),
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
    )

"""Environment-driven settings. No file-based config, no defaults that
silently point at a real deployment -- every value is either a genuinely
safe local-dev default or must be set explicitly."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
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
    oidc_discovery_uri: str
    oidc_jwks_uri_override: str
    # Exact browser origins allowed by CORS. Comma-separated FRONTEND_ORIGINS;
    # never a wildcard -- the backend only serves the product UI.
    frontend_origins: list[str]
    # Keyman extraction is a hard dependency of POST /api/posts/{id}/extract-keymen
    # only -- every other endpoint works with these unset. Empty string, not
    # a fabricated default, when unconfigured (see keyman_ingestion.py).
    orchestrator_base_url: str
    orchestrator_api_key: str
    # A vision-capable model name on the same contextual-orchestrator gateway
    # (orchestrator_base_url/_api_key) -- describes embedded post images
    # before an LLM call or embedding sees the post body (ADR: see
    # lineageweave/post_content_normalization.py). Empty means the image
    # channel is unavailable, same "no fake channel" discipline as every
    # other pluggable client.
    vision_model: str
    # Explicit semantic embedding model routed through contextual-orchestrator.
    # Empty means the embedding channel stays unavailable rather than using a
    # local heuristic vector.
    embedding_model: str
    # Event queue for post/ticket activity (XADD/XRANGE), per the brief's
    # "Event Queue, not MQ" requirement -- see backend/app/activity_stream.py.
    valkey_url: str
    # Self-hosted Searxng instance relation_verification.py's real client
    # checks Knowledge Graph relation inferences against (ADR 0005). Empty
    # means the verification channel is unavailable, same "no fake
    # channel" discipline as every other pluggable client.
    searxng_base_url: str
    # Optional TEPP HTTP transport. Empty keeps TeppClient's default
    # unavailable transport. Never a local psychometric substitute.
    tepp_transport_url: str
    tepp_api_key: str

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
    oidc_issuer = (keyverse_issuer or generic_oidc_issuer or keycloak_issuer).rstrip("/")
    oidc_discovery_uri = os.environ.get("KEYVERSE_DISCOVERY_URI", "").strip() or os.environ.get(
        "OIDC_DISCOVERY_URI", ""
    ).strip()
    if not oidc_discovery_uri:
        # The browser-facing issuer may be localhost in Compose, while this
        # backend must use the service DNS name to reach the same provider.
        discovery_base = oidc_issuer if (keyverse_issuer or generic_oidc_issuer) else keycloak_base_url
        oidc_discovery_uri = (
            f"{discovery_base.rstrip('/')}/realms/{keycloak_realm}/.well-known/openid-configuration"
            if not (keyverse_issuer or generic_oidc_issuer)
            else f"{discovery_base.rstrip('/')}/.well-known/openid-configuration"
        )
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
        oidc_client_id=(
            os.environ.get("KEYVERSE_CLIENT_ID", "").strip()
            or os.environ.get("OIDC_CLIENT_ID", "").strip()
            or keycloak_client_id
        ),
        oidc_discovery_uri=oidc_discovery_uri,
        oidc_jwks_uri_override=(
            os.environ.get("KEYVERSE_JWKS_URI", "").strip()
            or os.environ.get("OIDC_JWKS_URI", "").strip()
            or (
                f"{keycloak_base_url}/realms/{keycloak_realm}/protocol/openid-connect/certs"
                if not (keyverse_issuer or generic_oidc_issuer)
                else ""
            )
        ),
        frontend_origins=[
            origin.strip()
            for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ],
        orchestrator_base_url=os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        orchestrator_api_key=os.environ.get("ORCHESTRATOR_API_KEY", ""),
        vision_model=os.environ.get("VISION_MODEL", ""),
        embedding_model=os.environ.get("LLM_GATEWAY_EMBEDDING_MODEL", "").strip(),
        valkey_url=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
        searxng_base_url=os.environ.get("SEARXNG_BASE_URL", ""),
        tepp_transport_url=os.environ.get("TEPP_TRANSPORT_URL", ""),
        tepp_api_key=os.environ.get("TEPP_API_KEY", ""),
    )

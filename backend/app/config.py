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
    # Event queue for post/ticket activity (XADD/XRANGE), per the brief's
    # "Event Queue, not MQ" requirement -- see backend/app/activity_stream.py.
    valkey_url: str
    # Self-hosted Searxng instance relation_verification.py's real client
    # checks Knowledge Graph relation inferences against (ADR 0005). Empty
    # means the verification channel is unavailable, same "no fake
    # channel" discipline as every other pluggable client.
    searxng_base_url: str
    # RankWeave ranking port (ADR 0024). True = fail-closed
    # RankWeaveNotAvailable -- never invent a fused score. Default false
    # uses the in-process library already required by reconstruct.py.
    rankweave_disabled: bool
    # Keyverse identity port (ADR 0025). Empty = fail-closed
    # KeyverseNotAvailable -- never invent an issuer or account.
    keyverse_base_url: str

    @property
    def keycloak_jwks_uri(self) -> str:
        """JWKS URL the backend process itself can reach (internal DNS in compose)."""
        return f"{self.keycloak_base_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


def load_settings() -> Settings:
    """Read Settings from the environment, with local-dev defaults only."""
    keycloak_base_url = os.environ.get("KEYCLOAK_BASE_URL", "http://localhost:18080")
    keycloak_realm = os.environ.get("KEYCLOAK_REALM", "lineageweave-demo")
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
        frontend_origins=[
            origin.strip()
            for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ],
        orchestrator_base_url=os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        orchestrator_api_key=os.environ.get("ORCHESTRATOR_API_KEY", ""),
        vision_model=os.environ.get("VISION_MODEL", ""),
        valkey_url=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
        searxng_base_url=os.environ.get("SEARXNG_BASE_URL", ""),
        rankweave_disabled=os.environ.get("RANKWEAVE_DISABLED", "")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"},
        keyverse_base_url=os.environ.get("KEYVERSE_BASE_URL", ""),
    )

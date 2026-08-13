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
    )

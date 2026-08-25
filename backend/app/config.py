"""Environment-driven settings. No file-based config, no defaults that
silently point at a real deployment -- every value is either a genuinely
safe local-dev default or must be set explicitly."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

# Hard ceiling on one Global Ask job's answer computation, shared with the
# worker in global_ask_queue.py so config validation and execution can never
# disagree about the bound.
GLOBAL_ASK_JOB_DEADLINE_SECONDS = 600


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the backend's environment-driven configuration."""

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
    keyverse_claim_binding_required: bool
    # Exact browser origins allowed by CORS. Comma-separated FRONTEND_ORIGINS;
    # never a wildcard -- the backend only serves the product UI.
    frontend_origins: list[str]
    orchestrator_base_url: str
    orchestrator_api_key: str
    # Socket timeout for one Ask answer round-trip. Must stay below the Ask
    # worker's job deadline so the client, not the job reaper, ends a slow
    # call — hanging up earlier discards an answer the orchestrator has
    # already paid to generate (observed live as a BrokenPipe on its side).
    orchestrator_answer_timeout_seconds: float
    valkey_url: str
    searxng_base_url: str
    tepp_transport_url: str
    caldav_base_url: str
    naruon_calendar_base_url: str
    naruon_calendar_service_token: str
    rankweave_disabled: bool
    ontology_source_cursor_secret: str

    @property
    def keycloak_jwks_uri(self) -> str:
        """JWKS URL the backend process itself can reach (internal DNS in compose)."""
        return f"{self.keycloak_base_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


def _validated_answer_timeout(raw: str) -> float:
    """Parse the Ask answer timeout and hold it under the job deadline.

    The client must hang up before the worker's deadline reaper so a slow
    answer settles as a clean client timeout, never a reaped job — values
    at or above the deadline (or non-finite/non-positive ones) silently
    break that ordering, so they are configuration errors.
    """
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("ORCHESTRATOR_ANSWER_TIMEOUT_SECONDS must be a number") from exc
    if not math.isfinite(value) or not 0 < value < GLOBAL_ASK_JOB_DEADLINE_SECONDS:
        raise ValueError(
            "ORCHESTRATOR_ANSWER_TIMEOUT_SECONDS must be a finite number greater"
            f" than 0 and less than {GLOBAL_ASK_JOB_DEADLINE_SECONDS}"
        )
    return value


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
        keyverse_claim_binding_required=bool(keyverse_issuer),
        frontend_origins=[
            origin.strip()
            for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ],
        orchestrator_base_url=os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        orchestrator_api_key=os.environ.get("ORCHESTRATOR_API_KEY", ""),
        orchestrator_answer_timeout_seconds=_validated_answer_timeout(
            os.environ.get("ORCHESTRATOR_ANSWER_TIMEOUT_SECONDS", "570")
        ),
        valkey_url=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
        searxng_base_url=os.environ.get("SEARXNG_BASE_URL", ""),
        tepp_transport_url=os.environ.get("TEPP_TRANSPORT_URL", ""),
        caldav_base_url=os.environ.get("CALDAV_BASE_URL", "").strip(),
        naruon_calendar_base_url=os.environ.get("NARUON_CALENDAR_BASE_URL", "").strip(),
        naruon_calendar_service_token=os.environ.get(
            "NARUON_CALENDAR_SERVICE_TOKEN", ""
        ).strip(),
        rankweave_disabled=os.environ.get("RANKWEAVE_DISABLED", "")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"},
        ontology_source_cursor_secret=os.environ.get("ONTOLOGY_SOURCE_CURSOR_SECRET", "").strip(),
    )

"""Local OAuth helpers for integration tests that call the backend API.

These helpers are intentionally test-only. They exercise the confidential
machine clients already declared by the local realm; product browser login
remains Authorization Code + PKCE through ``lineageweave-frontend``.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from lineageweave.http_client import post_form


DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
REALM = "lineageweave-demo"
_VIEWER_CLIENT_ID = "lineageweave-test-automation"
_ADMIN_CLIENT_ID = "lineageweave-test-admin"
_VIEWER_SECRET_ENV = "KEYCLOAK_CLIENT_SECRET"
_ADMIN_SECRET_ENV = "KEYCLOAK_TEST_ADMIN_CLIENT_SECRET"
_VIEWER_DEV_SECRET = "lineageweave_test_automation_dev_only"
_ADMIN_DEV_SECRET = "lineageweave_test_admin_dev_only"
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _configured_keycloak_base_url(explicit_base_url: str | None) -> str:
    """Resolve the same Keycloak endpoint override used by the integration suite."""
    if explicit_base_url is not None:
        return explicit_base_url
    return os.environ.get("LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL", DEFAULT_KEYCLOAK_BASE_URL)


def _configured_client_secret(
    env_name: str,
    dev_secret: str,
    *,
    keycloak_base_url: str,
) -> str:
    """Resolve credentials without sending secrets over a remote cleartext endpoint."""
    parsed = urlsplit(keycloak_base_url)
    hostname = parsed.hostname
    if hostname not in _LOOPBACK_HOSTS and parsed.scheme != "https":
        raise RuntimeError(
            f"non-loopback Keycloak endpoint must use HTTPS: {keycloak_base_url!r}"
        )

    configured = os.environ.get(env_name)
    if configured:
        return configured
    if hostname in _LOOPBACK_HOSTS:
        return dev_secret
    raise RuntimeError(
        f"{env_name} must be set for non-loopback Keycloak endpoint {keycloak_base_url!r}"
    )


def _machine_access_token(
    *,
    keycloak_base_url: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Mint one local confidential-client token and reject malformed replies."""
    response = post_form(
        f"{keycloak_base_url}/realms/{REALM}/protocol/openid-connect/token",
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"{client_id} token response did not contain access_token")
    return token


def fetch_viewer_machine_token(
    keycloak_base_url: str | None = None,
) -> str:
    """Return the viewer-scoped automation token used by backend integration tests."""
    resolved_base_url = _configured_keycloak_base_url(keycloak_base_url)
    return _machine_access_token(
        keycloak_base_url=resolved_base_url,
        client_id=_VIEWER_CLIENT_ID,
        client_secret=_configured_client_secret(
            _VIEWER_SECRET_ENV,
            _VIEWER_DEV_SECRET,
            keycloak_base_url=resolved_base_url,
        ),
    )


def fetch_admin_machine_token(
    keycloak_base_url: str | None = None,
) -> str:
    """Return the distinct admin service token used for cross-account checks."""
    resolved_base_url = _configured_keycloak_base_url(keycloak_base_url)
    return _machine_access_token(
        keycloak_base_url=resolved_base_url,
        client_id=_ADMIN_CLIENT_ID,
        client_secret=_configured_client_secret(
            _ADMIN_SECRET_ENV,
            _ADMIN_DEV_SECRET,
            keycloak_base_url=resolved_base_url,
        ),
    )

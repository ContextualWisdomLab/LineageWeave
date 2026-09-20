"""Local OAuth helpers for integration tests that call the backend API.

These helpers are intentionally test-only. They exercise the confidential
machine clients already declared by the local realm; product browser login
remains Authorization Code + PKCE through ``lineageweave-frontend``.
"""

from __future__ import annotations

import os

from lineageweave.http_client import post_form


DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
REALM = "lineageweave-demo"
_VIEWER_CLIENT_ID = "lineageweave-test-automation"
_ADMIN_CLIENT_ID = "lineageweave-test-admin"
_VIEWER_SECRET_ENV = "KEYCLOAK_CLIENT_SECRET"
_ADMIN_SECRET_ENV = "KEYCLOAK_TEST_ADMIN_CLIENT_SECRET"
_VIEWER_DEV_SECRET = "lineageweave_test_automation_dev_only"
_ADMIN_DEV_SECRET = "lineageweave_test_admin_dev_only"


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
    keycloak_base_url: str = DEFAULT_KEYCLOAK_BASE_URL,
) -> str:
    """Return the viewer-scoped automation token used by backend integration tests."""
    return _machine_access_token(
        keycloak_base_url=keycloak_base_url,
        client_id=_VIEWER_CLIENT_ID,
        client_secret=os.environ.get(_VIEWER_SECRET_ENV, _VIEWER_DEV_SECRET),
    )


def fetch_admin_machine_token(
    keycloak_base_url: str = DEFAULT_KEYCLOAK_BASE_URL,
) -> str:
    """Return the distinct admin service token used for cross-account checks."""
    return _machine_access_token(
        keycloak_base_url=keycloak_base_url,
        client_id=_ADMIN_CLIENT_ID,
        client_secret=os.environ.get(_ADMIN_SECRET_ENV, _ADMIN_DEV_SECRET),
    )

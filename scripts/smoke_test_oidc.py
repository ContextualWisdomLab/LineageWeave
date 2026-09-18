#!/usr/bin/env python3
"""Checks the local demo Keycloak machine-token/JWKS/audience boundary.

This operator smoke obtains a short-lived access token for the synthetic local
``lineageweave-test-automation`` confidential client with the OAuth 2.0 Client
Credentials grant. It then fetches the realm's live JWKS and verifies the
returned token's RS256 signature, issuer, expiry, API audience, authorized
party, and subject.

This is intentionally machine-to-machine compatibility evidence, not browser
OIDC authorization-flow acceptance. The product browser path is exercised by
Playwright through the Keycloak-hosted login form and Authorization Code +
PKCE. Keeping the two actors separate prevents an automation shortcut from
being mistaken for product authentication evidence.

Canonical usage: KEYCLOAK_CLIENT_SECRET=... make smoke
Direct locked invocation:
  KEYCLOAK_CLIENT_SECRET=... uv run --locked --extra dev python scripts/smoke_test_oidc.py \
    [--base-url http://localhost:18080]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Keep repository imports available when the locked uv command runs from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt

from backend.app.config import load_settings
from lineageweave.http_client import HttpClientError, get_json, post_form
from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key

REALM = "lineageweave-demo"
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "lineageweave-test-automation")
API_AUDIENCE = "lineageweave-api"
POLL_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 2.0


def _wait_for_realm(issuer: str) -> None:
    discovery_url = f"{issuer}/.well-known/openid-configuration"
    last_error: Exception | None = None
    for _ in range(POLL_ATTEMPTS):
        try:
            get_json(discovery_url, timeout=5, service_peer_name="oidc")
            return
        except (HttpClientError, OSError, ValueError) as exc:
            last_error = exc
        time.sleep(POLL_INTERVAL_SECONDS)
    raise SystemExit(
        f"Keycloak realm '{REALM}' never became reachable at {discovery_url}: {last_error}"
    )


def run(base_url: str, client_secret: str) -> int:
    issuer = f"{base_url}/realms/{REALM}"
    token_endpoint = f"{issuer}/protocol/openid-connect/token"
    jwks_uri = f"{issuer}/protocol/openid-connect/certs"

    print(f"Waiting for {issuer} to accept connections...")
    _wait_for_realm(issuer)

    print(f"Requesting a machine token for '{CLIENT_ID}' via client credentials...")
    token_response = post_form(
        token_endpoint,
        {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    access_token = token_response["access_token"]

    print(f"Fetching live JWKS from {jwks_uri} and verifying the token's RS256 signature...")
    jwks = get_json(jwks_uri, timeout=10, service_peer_name="oidc")
    try:
        signing_key = select_rs256_signing_key(jwks, access_token)
    except JwksKeySelectionError as exc:
        raise SystemExit(f"machine token JWKS key rejected: {exc}") from exc
    claims = jwt.decode(
        access_token,
        key=signing_key,
        algorithms=["RS256"],
        issuer=issuer,
        audience=API_AUDIENCE,
        leeway=load_settings().oidc_clock_skew_seconds,
    )

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise SystemExit(f"machine token omitted a non-empty subject: {claims}")
    assert claims.get("azp") == CLIENT_ID, (
        f"machine token authorized party does not match {CLIENT_ID!r}: {claims}"
    )

    print("PASS: local Keycloak machine-token/JWKS/audience smoke verified.")
    print(f"  issuer:   {claims['iss']}")
    print(f"  subject:  {subject}")
    print(f"  client:   {claims['azp']}")
    print(f"  audience: {claims['aud']}")
    print(f"  expires:  {claims['exp']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:18080")
    args = parser.parse_args()
    client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
    if not client_secret:
        parser.error("set KEYCLOAK_CLIENT_SECRET for the local test-automation client")
    return run(args.base_url, client_secret)


if __name__ == "__main__":
    sys.exit(main())

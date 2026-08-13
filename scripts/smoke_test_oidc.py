#!/usr/bin/env python3
"""Proves the Docker Compose Keycloak stack does a real OIDC round-trip.

Not a check that Keycloak returns HTTP 200 -- an actual login (Resource
Owner Password Credentials grant, direct-access-grants, against a synthetic
demo user seeded by docker/keycloak/realm-export.json), followed by fetching
the realm's live JWKS and cryptographically verifying the returned access
token's RS256 signature, issuer, and expiry, then asserting the corp_code /
pu_code custom claims (the attributes the eventual FastAPI backend will read
for ABAC/RBAC scoping) came through.

Usage: python3 scripts/smoke_test_oidc.py [--base-url http://localhost:8080]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt
from jwt import PyJWKClient

REALM = "lineageweave-demo"
CLIENT_ID = "lineageweave-frontend"
DEMO_USERNAME = "demo.analyst"
DEMO_PASSWORD = "lineageweave-demo-only"  # nosec B105 -- throwaway local-dev-only Keycloak seed credential, see docker/keycloak/realm-export.json
POLL_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 2.0


def _post_form(url: str, fields: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 -- local dev Keycloak, http by design
        return json.loads(response.read().decode("utf-8"))


def _wait_for_realm(issuer: str) -> None:
    discovery_url = f"{issuer}/.well-known/openid-configuration"
    last_error: Exception | None = None
    for _ in range(POLL_ATTEMPTS):
        try:
            with urllib.request.urlopen(discovery_url, timeout=5) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError) as exc:
            last_error = exc
        time.sleep(POLL_INTERVAL_SECONDS)
    raise SystemExit(
        f"Keycloak realm '{REALM}' never became reachable at {discovery_url}: {last_error}"
    )


def run(base_url: str) -> int:
    issuer = f"{base_url}/realms/{REALM}"
    token_endpoint = f"{issuer}/protocol/openid-connect/token"
    jwks_uri = f"{issuer}/protocol/openid-connect/certs"

    print(f"Waiting for {issuer} to accept connections...")
    _wait_for_realm(issuer)

    print(f"Requesting a real token for '{DEMO_USERNAME}' via direct access grant...")
    token_response = _post_form(
        token_endpoint,
        {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD,
        },
    )
    access_token = token_response["access_token"]

    print(f"Fetching live JWKS from {jwks_uri} and verifying the token's RS256 signature...")
    jwk_client = PyJWKClient(jwks_uri)
    signing_key = jwk_client.get_signing_key_from_jwt(access_token)
    claims = jwt.decode(
        access_token,
        key=signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        # The eventual FastAPI backend registers itself as an audience once it
        # exists (Phase 1, task "FastAPI backend"); this smoke test only
        # proves the identity-provider round-trip, not backend-side audience
        # scoping, so audience verification is intentionally left to that
        # later, backend-specific check.
        options={"verify_aud": False},
    )

    assert claims["preferred_username"] == DEMO_USERNAME, claims
    assert claims.get("corp_code") == "DEMO-CORP-01", (
        f"corp_code claim missing or wrong -- protocol mapper misconfigured: {claims}"
    )
    assert claims.get("pu_code") == "DEMO-PU-A", (
        f"pu_code claim missing or wrong -- protocol mapper misconfigured: {claims}"
    )

    print("PASS: real login round-trip verified.")
    print(f"  issuer:    {claims['iss']}")
    print(f"  subject:   {claims['sub']}")
    print(f"  username:  {claims['preferred_username']}")
    print(f"  corp_code: {claims['corp_code']}")
    print(f"  pu_code:   {claims['pu_code']}")
    print(f"  expires:   {claims['exp']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:18080")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())

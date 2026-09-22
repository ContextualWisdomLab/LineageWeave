#!/usr/bin/env python3
"""Warm seeded post-content ingestion with the local machine OAuth actor.

The seed step inserts synthetic rows directly into Postgres. Post-content
extraction is lazy, so this script opens each seeded demo post through the
normal backend API after DB authorization for the confidential automation
client has been provisioned. It never authenticates a human fixture.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow `python3 scripts/warm_seeded_post_content.py` from a checkout without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from lineageweave.http_client import get_json, post_form


DEFAULT_POSTGRES_DSN = (
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
DEFAULT_BACKEND_BASE_URL = "http://localhost:18420"
AUTOMATION_CLIENT_ID = "lineageweave-test-automation"


def _machine_access_token(keycloak_base_url: str, client_secret: str) -> str:
    """Mint an API token for the validated local confidential automation client."""
    response = post_form(
        f"{keycloak_base_url}/realms/lineageweave-demo/protocol/openid-connect/token",
        {
            "grant_type": "client_credentials",
            "client_id": AUTOMATION_CLIENT_ID,
            "client_secret": client_secret,
        },
        timeout=30.0,
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("machine token response did not contain a non-empty access_token")
    return token


def _wait_for_backend(backend_base_url: str) -> None:
    """Wait for the local backend health endpoint before issuing warm-up reads."""
    for _ in range(60):
        try:
            get_json(f"{backend_base_url}/healthz", timeout=5.0)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError(
        f"backend at {backend_base_url} is not serving /healthz; run `make up` first"
    )


def _seeded_post_ids(postgres_dsn: str) -> list[str]:
    """Return ids for the synthetic demo posts that require lazy content ingestion."""
    connection = psycopg2.connect(postgres_dsn)
    try:
        with connection.cursor() as cur:
            cur.execute("select post_id from source_post where post_title like 'Demo %post'")
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        # psycopg2's context manager manages transactions, not connection lifetime.
        connection.close()


def warm_seeded_post_content(
    postgres_dsn: str,
    keycloak_base_url: str,
    backend_base_url: str,
    client_secret: str,
) -> int:
    """Open seeded post content through the production API path and return the count."""
    _wait_for_backend(backend_base_url)
    token = _machine_access_token(keycloak_base_url, client_secret)
    post_ids = _seeded_post_ids(postgres_dsn)
    for post_id in post_ids:
        get_json(
            f"{backend_base_url}/api/posts/{post_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
        )
    return len(post_ids)


def main() -> None:
    """Run the local machine warm-up after seed and service-account provisioning."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
    parser.add_argument("--keycloak-base-url", default=DEFAULT_KEYCLOAK_BASE_URL)
    parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL)
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("KEYCLOAK_CLIENT_SECRET"),
        help="Secret for lineageweave-test-automation (or KEYCLOAK_CLIENT_SECRET).",
    )
    args = parser.parse_args()
    if not args.client_secret:
        parser.error("set KEYCLOAK_CLIENT_SECRET or pass --client-secret")

    warmed = warm_seeded_post_content(
        args.postgres_dsn,
        args.keycloak_base_url,
        args.backend_base_url,
        args.client_secret,
    )
    print(f"Warmed post-content ingestion for {warmed} seeded posts")


if __name__ == "__main__":
    main()

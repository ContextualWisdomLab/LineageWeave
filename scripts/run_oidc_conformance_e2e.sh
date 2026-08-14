#!/usr/bin/env bash
set -euo pipefail

: "${LINEAGEWEAVE_E2E_DSN:?LINEAGEWEAVE_E2E_DSN is required}"
: "${LINEAGEWEAVE_E2E_SOURCE_TABLE:?LINEAGEWEAVE_E2E_SOURCE_TABLE is required}"

export LINEAGEWEAVE_E2E_KEYCLOAK_PORT="${LINEAGEWEAVE_E2E_KEYCLOAK_PORT:-18080}"
export LINEAGEWEAVE_E2E_VALKEY_PORT="${LINEAGEWEAVE_E2E_VALKEY_PORT:-16479}"
export LINEAGEWEAVE_E2E_PORT="${LINEAGEWEAVE_E2E_PORT:-18105}"
export LINEAGEWEAVE_E2E_OIDC_CLIENT_SECRET="${LINEAGEWEAVE_E2E_OIDC_CLIENT_SECRET:-lineageweave-e2e-client-fixture}"
export LINEAGEWEAVE_E2E_EMAIL="${LINEAGEWEAVE_E2E_EMAIL:-lineageweave-browser-e2e@example.test}"
export LINEAGEWEAVE_E2E_PASSWORD="${LINEAGEWEAVE_E2E_PASSWORD:-lineageweave-e2e-account-fixture}"
export LINEAGEWEAVE_E2E_ORG="${LINEAGEWEAVE_E2E_ORG:-E2E_CORP}"
export LINEAGEWEAVE_E2E_WORKSPACE="${LINEAGEWEAVE_E2E_WORKSPACE:-E2E_PU}"
export LINEAGEWEAVE_E2E_LOGIN_BASE_URL="http://127.0.0.1:${LINEAGEWEAVE_E2E_PORT}"
export LINEAGEWEAVE_E2E_AUTHENTICATED_BASE_URL="$LINEAGEWEAVE_E2E_LOGIN_BASE_URL"
export LINEAGEWEAVE_E2E_REQUIRE_KEYVERSE=1
export LINEAGEWEAVE_E2E_COMPLETE_LOGIN=1
export LINEAGEWEAVE_E2E_REQUIRE_DATA="${LINEAGEWEAVE_E2E_REQUIRE_DATA:-1}"

cleanup() {
  # Keep the conformance IdP and RP isolated from the next run and from any
  # operator-managed Compose project.  No volumes are removed.
  docker compose -f tests/compose.oidc-e2e.yml down >/dev/null 2>&1 || true
  docker compose -f tests/compose.oidc-conformance-idp.yml down >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker compose -f tests/compose.oidc-conformance-idp.yml up -d --wait
docker compose -f tests/compose.oidc-e2e.yml up -d --build --wait
node web/e2e/lineageweave.mjs

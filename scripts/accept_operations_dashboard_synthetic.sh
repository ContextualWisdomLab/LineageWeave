#!/usr/bin/env bash
set -euo pipefail

: "${EXPECTED_LINEAGEWEAVE_REVISION:?Set the exact LineageWeave revision used for the images}"
: "${K6_VUS:?Set the declared Dashboard concurrency}"
: "${K6_DURATION:?Set the declared Dashboard observation duration, including its unit}"
: "${OIDC_READINESS_TIMEOUT_SECONDS:?Set the declared synthetic OIDC readiness budget}"

BACKEND_URL="${BACKEND_URL:-http://localhost:18420}"
LINEAGEWEAVE_E2E_BASE_URL="${LINEAGEWEAVE_E2E_BASE_URL:-http://localhost:15173}"
LINEAGEWEAVE_OIDC_ISSUER="${LINEAGEWEAVE_OIDC_ISSUER:-http://localhost:18080/realms/lineageweave-demo}"
LINEAGEWEAVE_OIDC_CLIENT_ID="${LINEAGEWEAVE_OIDC_CLIENT_ID:-lineageweave-frontend}"
SYNTHETIC_USERNAME="${SYNTHETIC_USERNAME:-demo.admin}"
SYNTHETIC_PASSWORD="${SYNTHETIC_PASSWORD:-lineageweave-demo-only}"
SCREENSHOT_DESKTOP_PATH="${SCREENSHOT_DESKTOP_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-desktop.png}"
SCREENSHOT_MOBILE_PATH="${SCREENSHOT_MOBILE_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-mobile.png}"
E2E_OUTPUT_DIR="${E2E_OUTPUT_DIR:-/tmp/lineageweave-operations-dashboard-synthetic-e2e}"
K6_SUMMARY_PATH="${K6_SUMMARY_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-k6.json}"
PRODUCT_CONTAINER_PREFIX="${PRODUCT_CONTAINER_PREFIX:-lineageweave}"
repository_root="$(git rev-parse --show-toplevel)"

for artifact_path in "$SCREENSHOT_DESKTOP_PATH" "$SCREENSHOT_MOBILE_PATH" "$E2E_OUTPUT_DIR" "$K6_SUMMARY_PATH"; do
  case "$artifact_path" in
    "$repository_root"/*) echo "runtime evidence must stay outside the repository" >&2; exit 2 ;;
  esac
done
[[ "$SCREENSHOT_DESKTOP_PATH" != "$SCREENSHOT_MOBILE_PATH" ]] || {
  echo "desktop and mobile screenshots require distinct paths" >&2
  exit 2
}
[[ "$EXPECTED_LINEAGEWEAVE_REVISION" =~ ^[0-9a-f]{40}$ ]] || {
  echo "EXPECTED_LINEAGEWEAVE_REVISION must be a full commit SHA" >&2
  exit 2
}
[[ "$K6_VUS" =~ ^[1-9][0-9]*$ ]] || { echo "K6_VUS must be a positive integer" >&2; exit 2; }
[[ "$K6_DURATION" =~ ^[0-9]+([.][0-9]+)?(ms|s|m|h)$ ]] || {
  echo "K6_DURATION must include an explicit k6 duration unit" >&2
  exit 2
}
[[ "$OIDC_READINESS_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "OIDC_READINESS_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
}
for command_name in curl docker jq corepack k6; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 2; }
done

for service_name in backend backend-worker frontend; do
  container_name="${PRODUCT_CONTAINER_PREFIX}-${service_name}-1"
  actual_revision="$(docker inspect "$container_name" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')"
  [[ "$actual_revision" == "$EXPECTED_LINEAGEWEAVE_REVISION" ]] || {
    echo "$container_name image revision does not match the accepted revision" >&2
    exit 2
  }
done
frontend_issuer="$(docker inspect "${PRODUCT_CONTAINER_PREFIX}-frontend-1" --format '{{ index .Config.Labels "io.contextualwisdomlab.lineageweave.oidc-issuer" }}')"
frontend_backend_url="$(docker inspect "${PRODUCT_CONTAINER_PREFIX}-frontend-1" --format '{{ index .Config.Labels "io.contextualwisdomlab.lineageweave.backend-url" }}')"
[[ "$frontend_issuer" == "$LINEAGEWEAVE_OIDC_ISSUER" ]] || {
  echo "frontend image OIDC issuer does not match the acceptance issuer" >&2
  exit 2
}
[[ "$frontend_backend_url" == "$BACKEND_URL" ]] || {
  echo "frontend image backend URL does not match the acceptance backend" >&2
  exit 2
}

token_endpoint="${LINEAGEWEAVE_OIDC_ISSUER%/}/protocol/openid-connect/token"
oidc_deadline=$((SECONDS + OIDC_READINESS_TIMEOUT_SECONDS))
until curl --silent --fail --output /dev/null \
  "${LINEAGEWEAVE_OIDC_ISSUER%/}/.well-known/openid-configuration"; do
  (( SECONDS < oidc_deadline )) || { echo "synthetic OIDC did not become ready" >&2; exit 1; }
  sleep 1
done
LINEAGEWEAVE_ACCESS_TOKEN="$(curl --fail-with-body --silent --show-error \
  --data-urlencode "client_id=$LINEAGEWEAVE_OIDC_CLIENT_ID" \
  --data-urlencode 'grant_type=password' \
  --data-urlencode "username=$SYNTHETIC_USERNAME" \
  --data-urlencode "password=$SYNTHETIC_PASSWORD" \
  "$token_endpoint" | jq -er '.access_token')"

curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $LINEAGEWEAVE_ACCESS_TOKEN" \
  "$BACKEND_URL/api/dashboard" | jq -e '.cases | type == "array"' >/dev/null

export LINEAGEWEAVE_ACCESS_TOKEN LINEAGEWEAVE_OIDC_ISSUER LINEAGEWEAVE_OIDC_CLIENT_ID
export LINEAGEWEAVE_E2E_BASE_URL SCREENSHOT_DESKTOP_PATH SCREENSHOT_MOBILE_PATH
export REQUIRE_GROUNDED_CASE=false
(cd frontend && corepack pnpm exec playwright test \
  e2e/runtime-operations-dashboard.spec.ts --output "$E2E_OUTPUT_DIR")

export BACKEND_URL K6_VUS K6_DURATION
k6 run --vus "$K6_VUS" --duration "$K6_DURATION" \
  --summary-export "$K6_SUMMARY_PATH" scripts/k6_operations_dashboard.js
jq -e '.metrics.checks.values.fails == 0 and .metrics.http_req_failed.values.rate == 0' \
  "$K6_SUMMARY_PATH" >/dev/null

printf 'operations-dashboard-synthetic-acceptance-ok revision=%s\n' "$EXPECTED_LINEAGEWEAVE_REVISION"

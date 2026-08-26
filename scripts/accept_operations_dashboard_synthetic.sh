#!/usr/bin/env bash
set -euo pipefail

: "${EXPECTED_LINEAGEWEAVE_REVISION:?Set the exact LineageWeave revision used for the images}"
: "${K6_VUS:?Set the declared Dashboard concurrency}"
: "${K6_DURATION:?Set the declared Dashboard observation duration, including its unit}"

BACKEND_URL="${BACKEND_URL:-http://localhost:18420}"
LINEAGEWEAVE_E2E_BASE_URL="${LINEAGEWEAVE_E2E_BASE_URL:-http://localhost:15173}"
LINEAGEWEAVE_OIDC_ISSUER="${LINEAGEWEAVE_OIDC_ISSUER:-http://localhost:18080/realms/lineageweave-demo}"
LINEAGEWEAVE_OIDC_CLIENT_ID="${LINEAGEWEAVE_OIDC_CLIENT_ID:-lineageweave-frontend}"
SYNTHETIC_USERNAME="${SYNTHETIC_USERNAME:-demo.analyst}"
SYNTHETIC_PASSWORD="${SYNTHETIC_PASSWORD:-lineageweave-demo-only}"
SCREENSHOT_DESKTOP_PATH="${SCREENSHOT_DESKTOP_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-desktop.png}"
SCREENSHOT_MOBILE_PATH="${SCREENSHOT_MOBILE_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-mobile.png}"
E2E_OUTPUT_DIR="${E2E_OUTPUT_DIR:-/tmp/lineageweave-operations-dashboard-synthetic-e2e}"
K6_SUMMARY_PATH="${K6_SUMMARY_PATH:-/tmp/lineageweave-operations-dashboard-synthetic-k6.json}"
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
for command_name in curl docker jq corepack k6; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 2; }
done

for container_name in lineageweave-backend-1 lineageweave-backend-worker-1 lineageweave-frontend-1; do
  actual_revision="$(docker inspect "$container_name" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')"
  [[ "$actual_revision" == "$EXPECTED_LINEAGEWEAVE_REVISION" ]] || {
    echo "$container_name image revision does not match the accepted revision" >&2
    exit 2
  }
done

token_endpoint="${LINEAGEWEAVE_OIDC_ISSUER%/}/protocol/openid-connect/token"
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

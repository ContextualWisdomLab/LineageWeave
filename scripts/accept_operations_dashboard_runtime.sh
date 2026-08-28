#!/usr/bin/env bash
set -euo pipefail
export COMPOSE_FILE=docker-compose.yml

: "${ALLOW_PROVIDER_CALLS:?Set ALLOW_PROVIDER_CALLS=1 only after the readiness-lease fix is deployed}"
: "${EXPECTED_ORCHESTRATOR_REVISION:?Set the exact merged contextual-orchestrator revision}"
: "${EXPECTED_LINEAGEWEAVE_REVISION:?Set the exact LineageWeave revision used for the images}"
: "${ORCHESTRATOR_ADMIN_TOKEN:?Set the runtime admin token}"
: "${LINEAGEWEAVE_ACCESS_TOKEN:?Set an authorized post_admin access token}"
: "${LINEAGEWEAVE_OIDC_ISSUER:?Set the frontend OIDC issuer}"
: "${LINEAGEWEAVE_OIDC_CLIENT_ID:?Set the frontend OIDC client id}"
: "${K6_VUS:?Set the declared Dashboard concurrency}"
: "${K6_DURATION:?Set the declared Dashboard observation duration, including its unit}"
: "${BACKEND_READINESS_TIMEOUT_SECONDS:?Set the declared backend readiness budget}"
[[ "$ALLOW_PROVIDER_CALLS" == "1" ]] || { echo "provider calls are not authorized" >&2; exit 2; }
[[ "$EXPECTED_LINEAGEWEAVE_REVISION" =~ ^[0-9a-f]{40}$ ]] || {
  echo "EXPECTED_LINEAGEWEAVE_REVISION must be a full commit SHA" >&2
  exit 2
}

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:18000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:18420}"
LINEAGEWEAVE_E2E_BASE_URL="${LINEAGEWEAVE_E2E_BASE_URL:-http://localhost:15173}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-lineageweave-postgres-1}"
SCREENSHOT_DESKTOP_PATH="${SCREENSHOT_DESKTOP_PATH:-/tmp/lineageweave-operations-dashboard-runtime-desktop.png}"
SCREENSHOT_MOBILE_PATH="${SCREENSHOT_MOBILE_PATH:-/tmp/lineageweave-operations-dashboard-runtime-mobile.png}"
ASK_SCREENSHOT_DESKTOP_PATH="${ASK_SCREENSHOT_DESKTOP_PATH:-/tmp/lineageweave-ask-runtime-desktop.png}"
ASK_SCREENSHOT_MOBILE_PATH="${ASK_SCREENSHOT_MOBILE_PATH:-/tmp/lineageweave-ask-runtime-mobile.png}"
E2E_OUTPUT_DIR="${E2E_OUTPUT_DIR:-/tmp/lineageweave-operations-dashboard-e2e}"
K6_SUMMARY_PATH="${K6_SUMMARY_PATH:-/tmp/lineageweave-operations-dashboard-k6.json}"
repository_root="$(git rev-parse --show-toplevel)"
for screenshot_path in "$SCREENSHOT_DESKTOP_PATH" "$SCREENSHOT_MOBILE_PATH" "$ASK_SCREENSHOT_DESKTOP_PATH" "$ASK_SCREENSHOT_MOBILE_PATH"; do
  case "$screenshot_path" in
    "$repository_root"/*) echo "runtime screenshots must stay outside the repository" >&2; exit 2 ;;
  esac
done
[[ "$SCREENSHOT_DESKTOP_PATH" != "$SCREENSHOT_MOBILE_PATH" ]] || {
  echo "desktop and mobile screenshots require distinct paths" >&2
  exit 2
}
[[ "$ASK_SCREENSHOT_DESKTOP_PATH" != "$ASK_SCREENSHOT_MOBILE_PATH" ]] || {
  echo "Ask desktop and mobile screenshots require distinct paths" >&2
  exit 2
}
case "$E2E_OUTPUT_DIR" in
  "$repository_root"/*) echo "runtime browser artifacts must stay outside the repository" >&2; exit 2 ;;
esac
case "$K6_SUMMARY_PATH" in
  "$repository_root"/*) echo "runtime load evidence must stay outside the repository" >&2; exit 2 ;;
esac
[[ "$K6_VUS" =~ ^[1-9][0-9]*$ ]] || { echo "K6_VUS must be a positive integer" >&2; exit 2; }
[[ "$K6_DURATION" =~ ^[0-9]+([.][0-9]+)?(ms|s|m|h)$ ]] || {
  echo "K6_DURATION must include an explicit k6 duration unit" >&2
  exit 2
}
[[ "$BACKEND_READINESS_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "BACKEND_READINESS_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
}

for command_name in curl docker jq corepack k6 uv; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 2; }
done

actual_revision="$(docker inspect lineageweave-orchestrator-1 --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')"
[[ "$actual_revision" == "$EXPECTED_ORCHESTRATOR_REVISION" ]] || {
  echo "orchestrator image revision does not match the accepted revision" >&2
  exit 2
}
for service_name in backend backend-worker frontend; do
  product_revision="$(docker inspect "lineageweave-${service_name}-1" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')"
  [[ "$product_revision" == "$EXPECTED_LINEAGEWEAVE_REVISION" ]] || {
    echo "lineageweave-${service_name}-1 image revision does not match the accepted revision" >&2
    exit 2
  }
done
frontend_issuer="$(docker inspect lineageweave-frontend-1 --format '{{ index .Config.Labels "io.contextualwisdomlab.lineageweave.oidc-issuer" }}')"
frontend_backend_url="$(docker inspect lineageweave-frontend-1 --format '{{ index .Config.Labels "io.contextualwisdomlab.lineageweave.backend-url" }}')"
[[ "$frontend_issuer" == "$LINEAGEWEAVE_OIDC_ISSUER" ]] || {
  echo "frontend image OIDC issuer does not match the acceptance issuer" >&2
  exit 2
}
[[ "$frontend_backend_url" == "$BACKEND_URL" ]] || {
  echo "frontend image backend URL does not match the acceptance backend" >&2
  exit 2
}

source_post_eligibility_sql="$(uv run python -c \
  'from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL; print(SOURCE_POST_ELIGIBILITY_SQL.format(alias="post"))')"
backend_deadline=$((SECONDS + BACKEND_READINESS_TIMEOUT_SECONDS))
until curl --silent --fail --output /dev/null "${BACKEND_URL%/}/healthz"; do
  (( SECONDS < backend_deadline )) || { echo "backend did not become ready" >&2; exit 1; }
  sleep 1
done

curl_json() {
  local token="$1" method="$2" url="$3" body="${4:-}"
  if [[ -n "$body" ]]; then
    local escaped_body="${body//\\/\\\\}"
    escaped_body="${escaped_body//\"/\\\"}"
    curl --fail-with-body --silent --show-error --config - <<EOF
url = "$url"
request = "$method"
header = "Authorization: Bearer $token"
header = "Content-Type: application/json"
data = "$escaped_body"
EOF
  else
    curl --fail-with-body --silent --show-error --config - <<EOF
url = "$url"
request = "$method"
header = "Authorization: Bearer $token"
EOF
  fi
}

# This explicit refresh is the first provider call. The revision gate above
# prevents an older runtime from reacquiring readiness work without the lease fix.
curl_json "$ORCHESTRATOR_ADMIN_TOKEN" GET \
  "$ORCHESTRATOR_URL/api/v1/provider_readiness/latest?refresh=true" \
  | jq -e '.status == "ready" and .ready_agent_count > 0' >/dev/null

aggregate_sql="
with preferred as (
    select post.post_id
      from source_post post
      join post_content_ingestion_job job on job.post_id = post.post_id
     where ${source_post_eligibility_sql}
       and job.status_code = 'post_content_ingestion_succeeded'
       and exists (
           select 1 from post_project_mention project
            where project.post_id = post.post_id
              and nullif(btrim(project.ontology_iri), '') is not null
       )
       and not exists (
           select 1 from operations_case_analysis analysis
            where analysis.post_id = post.post_id
              and analysis.source_body_sha256 = job.source_body_sha256
       )
), grounded as (
    select distinct classification.post_id, classification.case_kind_code
      from operations_case_classification classification
     where nullif(btrim(classification.evidence_text), '') is not null
       and classification.evidence_post_id is not null
       and classification.evidence_input_sha256 is not null
)
select (select count(*) from preferred),
       (select count(*) from operations_case_analysis),
       (select count(*) from grounded);
"

IFS='|' read -r preferred_before analysis_before grounded_before <<<"$(
  docker exec "$POSTGRES_CONTAINER" psql -X -U lineageweave -d lineageweave \
    -AtF '|' -c "$aggregate_sql"
)"
[[ "$preferred_before" == "1" ]] || {
  echo "expected exactly one normalized preferred candidate; observed $preferred_before" >&2
  exit 1
}

curl_json "$LINEAGEWEAVE_ACCESS_TOKEN" POST \
  "$BACKEND_URL/api/post-content/backfill" '{"limit":1}' \
  | jq -e '.selected_posts == 1 and .queued_posts == 1' >/dev/null

deadline=$((SECONDS + 600))
while (( SECONDS < deadline )); do
  IFS='|' read -r preferred_after analysis_after grounded_after <<<"$(
    docker exec "$POSTGRES_CONTAINER" psql -X -U lineageweave -d lineageweave \
      -AtF '|' -c "$aggregate_sql"
  )"
  if [[ "$preferred_after" == "0" \
     && "$analysis_after" -gt "$analysis_before" \
     && "$grounded_after" -gt "$grounded_before" ]]; then
    break
  fi
  sleep 2
done
[[ "${preferred_after:-1}" == "0" \
   && "${analysis_after:-0}" -gt "$analysis_before" \
   && "${grounded_after:-0}" -gt "$grounded_before" ]] || {
  echo "grounded operations-case acceptance did not complete before the deadline" >&2
  exit 1
}

curl_json "$LINEAGEWEAVE_ACCESS_TOKEN" GET "$BACKEND_URL/api/dashboard" \
  | jq -e '.cases | length > 0' >/dev/null

export LINEAGEWEAVE_ACCESS_TOKEN LINEAGEWEAVE_OIDC_ISSUER LINEAGEWEAVE_OIDC_CLIENT_ID
export LINEAGEWEAVE_E2E_BASE_URL SCREENSHOT_DESKTOP_PATH SCREENSHOT_MOBILE_PATH
export ASK_SCREENSHOT_DESKTOP_PATH ASK_SCREENSHOT_MOBILE_PATH
(cd frontend && corepack pnpm exec playwright test \
  e2e/runtime-operations-dashboard.spec.ts e2e/ask-agent.spec.ts --output "$E2E_OUTPUT_DIR")

export BACKEND_URL LINEAGEWEAVE_ACCESS_TOKEN K6_VUS K6_DURATION
k6 run --vus "$K6_VUS" --duration "$K6_DURATION" \
  --summary-export "$K6_SUMMARY_PATH" scripts/k6_operations_dashboard.js
jq -e '.metrics.checks.fails == 0 and .metrics.http_req_failed.value == 0' \
  "$K6_SUMMARY_PATH" >/dev/null

printf 'operations-dashboard-runtime-acceptance-ok preferred=%s analysis_delta=%s grounded_delta=%s\n' \
  "$preferred_after" "$((analysis_after - analysis_before))" "$((grounded_after - grounded_before))"

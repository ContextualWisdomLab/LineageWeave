#!/usr/bin/env bash
set -euo pipefail
export COMPOSE_FILE=docker-compose.yml

: "${ALLOW_PROVIDER_CALLS:?Set ALLOW_PROVIDER_CALLS=1 only after the readiness-lease fix is deployed}"
: "${EXPECTED_ORCHESTRATOR_REVISION:?Set the exact merged contextual-orchestrator revision}"
: "${EXPECTED_LINEAGEWEAVE_REVISION:?Set the exact LineageWeave revision used for the images}"
: "${LINEAGEWEAVE_ACCESS_TOKEN:?Set an authorized post_admin access token}"
: "${LINEAGEWEAVE_OIDC_ISSUER:?Set the frontend OIDC issuer}"
: "${LINEAGEWEAVE_OIDC_CLIENT_ID:?Set the frontend OIDC client id}"
: "${LINEAGEWEAVE_RUNTIME_ASK_QUESTION:?Set one non-identifying runtime Ask question}"
: "${LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS:?Set the declared runtime Ask observation budget}"
: "${K6_VUS:?Set the declared Dashboard concurrency}"
: "${K6_DURATION:?Set the declared Dashboard observation duration, including its unit}"
: "${BACKEND_READINESS_TIMEOUT_SECONDS:?Set the declared backend readiness budget}"
: "${ORCHESTRATOR_PROBE_TIMEOUT_SECONDS:?Set the declared per-agent provider probe timeout (0.1 through 30 seconds)}"
: "${ORCHESTRATOR_READINESS_TIMEOUT_SECONDS:?Set the declared readiness-job observation budget}"
: "${OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS:?Set the declared operations-case observation budget}"
: "${OPERATIONS_CASE_POLL_SECONDS:?Set the declared operations-case observation cadence}"
[[ ",${COMPOSE_PROFILES:-}," == *,mcp,* ]] || {
  echo "start the accepted stack with COMPOSE_PROFILES=mcp so MCP evidence is included" >&2
  exit 2
}
[[ "$ALLOW_PROVIDER_CALLS" == "1" ]] || { echo "provider calls are not authorized" >&2; exit 2; }
[[ "$EXPECTED_LINEAGEWEAVE_REVISION" =~ ^[0-9a-f]{40}$ ]] || {
  echo "EXPECTED_LINEAGEWEAVE_REVISION must be a full commit SHA" >&2
  exit 2
}

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
screenshot_paths=("$SCREENSHOT_DESKTOP_PATH" "$SCREENSHOT_MOBILE_PATH" "$ASK_SCREENSHOT_DESKTOP_PATH" "$ASK_SCREENSHOT_MOBILE_PATH")
for screenshot_path in "${screenshot_paths[@]}"; do
  case "$screenshot_path" in
    "$repository_root"/*) echo "runtime screenshots must stay outside the repository" >&2; exit 2 ;;
  esac
done
for ((left_index = 0; left_index < ${#screenshot_paths[@]}; left_index++)); do
  for ((right_index = left_index + 1; right_index < ${#screenshot_paths[@]}; right_index++)); do
    [[ "${screenshot_paths[$left_index]}" != "${screenshot_paths[$right_index]}" ]] || {
      echo "runtime screenshots require four distinct paths" >&2
      exit 2
    }
  done
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
jq -en --arg value "$ORCHESTRATOR_PROBE_TIMEOUT_SECONDS" \
  '($value | tonumber) >= 0.1 and ($value | tonumber) <= 30' >/dev/null || {
  echo "ORCHESTRATOR_PROBE_TIMEOUT_SECONDS must be between 0.1 and 30" >&2
  exit 2
}
[[ "$ORCHESTRATOR_READINESS_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "ORCHESTRATOR_READINESS_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
}
[[ "$OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
}
[[ "$OPERATIONS_CASE_POLL_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "OPERATIONS_CASE_POLL_SECONDS must be a positive integer" >&2
  exit 2
}
[[ "$LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS must be a positive integer" >&2
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
docker inspect lineageweave-mcp-1 >/dev/null 2>&1 || {
  echo "start the accepted stack with COMPOSE_PROFILES=mcp before running acceptance" >&2
  exit 2
}
for service_name in backend backend-worker mcp frontend; do
  product_revision="$(docker inspect "lineageweave-${service_name}-1" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')"
  [[ "$product_revision" == "$EXPECTED_LINEAGEWEAVE_REVISION" ]] || {
    echo "lineageweave-${service_name}-1 image revision does not match the accepted revision" >&2
    exit 2
  }
done
worker_started_at="$(docker inspect lineageweave-backend-worker-1 --format '{{.State.StartedAt}}')"
[[ -n "$worker_started_at" && "$worker_started_at" != "0001-01-01T00:00:00Z" ]] || {
  echo "backend worker has no exact deployment start instant" >&2
  exit 1
}
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

orchestrator_json() {
  local method="$1" path="$2" body="${3:-}" request_timeout_ms="$4"
  docker exec -i \
    lineageweave-orchestrator-1 \
    python - "$method" "$path" "$body" "$request_timeout_ms" <<'PY'
import os
import sys
import urllib.request

method, path, body, timeout_ms = sys.argv[1:]
headers = {
    "Authorization": f"Bearer {os.environ['CONTEXTUAL_ORCHESTRATOR_TOKEN']}"
}
data = None
if body:
    headers["Content-Type"] = "application/json"
    data = body.encode("utf-8")
if timeout_ms:
    headers["X-Request-Timeout-Ms"] = timeout_ms
request = urllib.request.Request(
    f"http://127.0.0.1:8000{path}",
    data=data,
    headers=headers,
    method=method,
)
with urllib.request.urlopen(request, timeout=max(float(timeout_ms) / 1000, 1.0)) as response:
    sys.stdout.write(response.read().decode("utf-8"))
PY
}

# This explicit bounded refresh is the first provider call. Read the cached
# catalog first and probe only active agents from the configured gateway.
readiness_deadline=$((SECONDS + ORCHESTRATOR_READINESS_TIMEOUT_SECONDS))
remaining_readiness_ms() {
  local remaining_seconds=$((readiness_deadline - SECONDS))
  (( remaining_seconds > 0 )) || return 1
  printf '%d' "$((remaining_seconds * 1000))"
}
readiness_timeout_ms="$(remaining_readiness_ms)" || {
  echo "provider readiness exhausted its declared observation budget before catalog read" >&2
  exit 1
}
cached_readiness="$(orchestrator_json GET \
  /api/v1/provider_readiness/latest "" "$readiness_timeout_ms")"
configured_agent_ids="$(jq -ce \
  '[.items[] | select(.provider == "configured_gateway" and .status != "disabled") | .agent_id] | unique | select(length > 0)' \
  <<<"$cached_readiness")" || {
  echo "no active configured-gateway agents are available for readiness verification" >&2
  exit 1
}
readiness_request="$(jq -cn \
  --argjson agent_ids "$configured_agent_ids" \
  --argjson timeout_seconds "$ORCHESTRATOR_PROBE_TIMEOUT_SECONDS" \
  '{agent_ids:$agent_ids,capability_code:"structured",timeout_seconds:$timeout_seconds}')"
readiness_timeout_ms="$(remaining_readiness_ms)" || {
  echo "provider readiness exhausted its declared observation budget before job submission" >&2
  exit 1
}
readiness_job="$(orchestrator_json POST \
  /api/v1/provider_readiness_refreshes "$readiness_request" "$readiness_timeout_ms")"
readiness_job_id="$(jq -er '.job_id | select(type == "string" and length > 0)' \
  <<<"$readiness_job")"
while (( SECONDS < readiness_deadline )); do
  readiness_status="$(jq -er '.status' <<<"$readiness_job")"
  case "$readiness_status" in
    completed)
      jq -e '.ready_count > 0' <<<"$readiness_job" >/dev/null || {
        echo "provider readiness completed without an available configured-gateway agent" >&2
        exit 1
      }
      break
      ;;
    queued|running)
      readiness_poll_after_ms="$(jq -er \
        '.poll_after_ms | select(type == "number" and floor == . and . > 0)' \
        <<<"$readiness_job")" || {
        echo "provider readiness did not declare a valid polling cadence" >&2
        exit 1
      }
      readiness_timeout_ms="$(remaining_readiness_ms)" || break
      (( readiness_poll_after_ms < readiness_timeout_ms )) || break
      readiness_poll_seconds="$(jq -nr \
        --argjson poll_after_ms "$readiness_poll_after_ms" \
        '$poll_after_ms / 1000')"
      sleep "$readiness_poll_seconds"
      readiness_timeout_ms="$(remaining_readiness_ms)" || break
      readiness_job="$(orchestrator_json GET \
        "/api/v1/provider_readiness_refreshes/$readiness_job_id" "" "$readiness_timeout_ms")"
      ;;
    failed|cancelled|expired)
      echo "provider readiness ended before an agent became available; restore access and rerun acceptance" >&2
      exit 1
      ;;
    *)
      echo "provider readiness returned an unsupported job state" >&2
      exit 1
      ;;
  esac
done
[[ "${readiness_status:-}" == "completed" ]] || {
  echo "provider readiness did not complete within the declared observation budget" >&2
  exit 1
}

aggregate_sql="
with eligible_jobs as materialized (
    select post.post_id, job.source_body_sha256, job.status_code
      from source_post post
      join post_content_ingestion_job job on job.post_id = post.post_id
     where ${source_post_eligibility_sql}
       and exists (
           select 1 from post_project_mention project
            where project.post_id = post.post_id
              and nullif(btrim(project.ontology_iri), '') is not null
       )
), inflight as (
    select job.post_id
      from eligible_jobs job
     where job.status_code in (
               'post_content_ingestion_queued',
               'post_content_ingestion_running'
           )
       and not exists (
           select 1 from operations_case_analysis analysis
            where analysis.post_id = job.post_id
              and analysis.source_body_sha256 = job.source_body_sha256
       )
), deployed_analyses as (
    select analysis.post_id
      from eligible_jobs job
      join operations_case_analysis analysis
        on analysis.post_id = job.post_id
       and analysis.source_body_sha256 = job.source_body_sha256
     where analysis.analyzed_at >= :'deployment_started_at'::timestamptz
), deployed_grounded as (
    select analysis.post_id
      from deployed_analyses analysis
     where exists (
         select 1 from operations_case_classification classification
          where classification.post_id = analysis.post_id
            and nullif(btrim(classification.evidence_text), '') is not null
            and classification.evidence_post_id is not null
            and classification.evidence_input_sha256 is not null
     )
)
select (select count(distinct post_id) from inflight),
       (select count(distinct post_id) from deployed_analyses),
       (select count(distinct post_id) from deployed_grounded);
"

IFS='|' read -r inflight_before analysis_before grounded_before <<<"$(
  docker exec "$POSTGRES_CONTAINER" psql -X -U lineageweave -d lineageweave \
    -v deployment_started_at="$worker_started_at" -AtF '|' -c "$aggregate_sql"
)"
if (( grounded_before > 0 )); then
  inflight_after="$inflight_before"
  analysis_after="$analysis_before"
  grounded_after="$grounded_before"
else
  (( inflight_before > 0 )) || {
    echo "no deployment-grounded analysis or active eligible candidate is available" >&2
    exit 1
  }
  deadline=$((SECONDS + OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    IFS='|' read -r inflight_after analysis_after grounded_after <<<"$(
    docker exec "$POSTGRES_CONTAINER" psql -X -U lineageweave -d lineageweave \
      -v deployment_started_at="$worker_started_at" -AtF '|' -c "$aggregate_sql"
    )"
    if (( analysis_after > analysis_before && grounded_after > grounded_before )); then
      break
    fi
    sleep "$OPERATIONS_CASE_POLL_SECONDS"
  done
  (( ${analysis_after:-0} > analysis_before \
     && ${grounded_after:-0} > grounded_before )) || {
    echo "grounded operations-case acceptance did not complete before the deadline" >&2
    exit 1
  }
fi

curl_json "$LINEAGEWEAVE_ACCESS_TOKEN" GET "$BACKEND_URL/api/dashboard" \
  | jq -e '.cases | length > 0' >/dev/null

export LINEAGEWEAVE_ACCESS_TOKEN LINEAGEWEAVE_OIDC_ISSUER LINEAGEWEAVE_OIDC_CLIENT_ID
export LINEAGEWEAVE_E2E_BASE_URL SCREENSHOT_DESKTOP_PATH SCREENSHOT_MOBILE_PATH
export ASK_SCREENSHOT_DESKTOP_PATH ASK_SCREENSHOT_MOBILE_PATH
(cd frontend && corepack pnpm exec playwright test \
  e2e/runtime-operations-dashboard.spec.ts e2e/runtime-ask-evidence.spec.ts --output "$E2E_OUTPUT_DIR")

export BACKEND_URL LINEAGEWEAVE_ACCESS_TOKEN K6_VUS K6_DURATION
k6 run --vus "$K6_VUS" --duration "$K6_DURATION" \
  --summary-export "$K6_SUMMARY_PATH" scripts/k6_operations_dashboard.js
jq -e '.metrics.checks.fails == 0 and .metrics.http_req_failed.value == 0' \
  "$K6_SUMMARY_PATH" >/dev/null

printf 'operations-dashboard-runtime-acceptance-ok inflight=%s deployment_analysis=%s deployment_grounded=%s\n' \
  "$inflight_after" "$analysis_after" "$grounded_after"

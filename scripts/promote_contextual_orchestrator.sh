#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_PROVIDER_CALLS:?Set to 1 to authorize the bounded readiness probe}"
: "${EXPECTED_ORCHESTRATOR_REVISION:?Set the exact 40-character candidate revision}"
: "${ORCHESTRATOR_PROBE_TIMEOUT_SECONDS:?Set the declared per-agent probe timeout}"
: "${ORCHESTRATOR_READINESS_TIMEOUT_SECONDS:?Set the declared readiness observation budget}"
: "${ORCHESTRATOR_STARTUP_TIMEOUT_SECONDS:?Set the declared container startup budget}"
[[ "$ALLOW_PROVIDER_CALLS" == "1" ]] || { echo "provider calls are not authorized" >&2; exit 2; }
[[ "$EXPECTED_ORCHESTRATOR_REVISION" =~ ^[0-9a-f]{40}$ ]] || { echo "expected revision must be a full commit SHA" >&2; exit 2; }
[[ "$ORCHESTRATOR_STARTUP_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || {
  echo "startup timeout must be a positive integer" >&2
  exit 2
}

export COMPOSE_FILE=docker-compose.yml
preflight_container="${COMPOSE_PROJECT_NAME:-lineageweave}-orchestrator-preflight"
docker inspect "$preflight_container" >/dev/null 2>&1 && {
  echo "preflight container already exists; inspect it before retrying" >&2
  exit 1
}
cleanup() { docker rm -f "$preflight_container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker compose build orchestrator
image_ref="$(docker compose config --format json | python -c \
  'import json, sys; print(json.load(sys.stdin)["services"]["orchestrator"]["image"])')"
[[ -n "$image_ref" ]] || { echo "candidate orchestrator image was not configured" >&2; exit 1; }
image_revision="$(docker image inspect "$image_ref" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')"
[[ "$image_revision" == "$EXPECTED_ORCHESTRATOR_REVISION" ]] || {
  echo "candidate image revision does not match the requested promotion" >&2
  exit 1
}

docker compose run -d --no-deps --name "$preflight_container" orchestrator >/dev/null
startup_deadline=$((SECONDS + ORCHESTRATOR_STARTUP_TIMEOUT_SECONDS))
until [[ "$(docker inspect "$preflight_container" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}')" == "healthy" ]]; do
  (( SECONDS < startup_deadline )) || { echo "candidate orchestrator did not become healthy" >&2; exit 1; }
  sleep 1
done

python scripts/verify_orchestrator_provider_readiness.py \
  --container "$preflight_container" \
  --probe-timeout-seconds "$ORCHESTRATOR_PROBE_TIMEOUT_SECONDS" \
  --readiness-timeout-seconds "$ORCHESTRATOR_READINESS_TIMEOUT_SECONDS"

# Recreate only after the isolated candidate proves that the current Compose
# env_file can authenticate the configured endpoint.
docker compose up -d --no-deps orchestrator
canonical_container="${COMPOSE_PROJECT_NAME:-lineageweave}-orchestrator-1"
canonical_revision="$(docker inspect "$canonical_container" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')"
[[ "$canonical_revision" == "$EXPECTED_ORCHESTRATOR_REVISION" ]] || {
  echo "promoted orchestrator revision does not match the accepted candidate" >&2
  exit 1
}

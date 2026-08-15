#!/usr/bin/env bash
set -euo pipefail

: "${LINEAGEWEAVE_DSN:?LINEAGEWEAVE_DSN is required}"
: "${LINEAGE_SOURCE_TABLE:?LINEAGE_SOURCE_TABLE is required}"

emit_audit_json_line() {
  local event_name="$1"
  shift || true
  local event_time
  event_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python - "$event_name" "$event_time" "$@" <<'PY'
import json
import sys

event = sys.argv[1]
event_time = sys.argv[2]
payload = {"event": event, "timestamp_utc": event_time}
for arg in sys.argv[3:]:
    if "=" not in arg:
        continue
    key, value = arg.split("=", 1)
    payload[key] = value
print("lineageweave_audit_log=" + json.dumps(payload, ensure_ascii=False))
PY
}

query_open_pull_requests() {
  local repo="$1"
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh_unavailable"
    return 0
  fi
  local count
  if ! count="$(gh pr list -R "$repo" --state open --json number --limit 200 --jq 'length' 2>/dev/null)"; then
    echo "gh_api_error"
    return 0
  fi
  printf '%s\n' "${count:-0}"
}

audit_exit_code=0

JSON_OUT=${LINEAGEWEAVE_JSON_OUT:-}
ANALYTICS_OUT=${LINEAGEWEAVE_ANALYTICS_OUT:-}
json_out_audit=${JSON_OUT:-disabled}
analytics_out_audit=${ANALYTICS_OUT:-disabled}
KEYMAN_LIMIT=${LINEAGEWEAVE_KEYMAN_LIMIT:-0}
LIMIT=${LINEAGEWEAVE_LIMIT:-0}
TIMEOUT_PRODUCT=${LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT:-120}
TIMEOUT_KEYMAN=${LINEAGEWEAVE_KEYMAN_LLM_TIMEOUT:-45}
TIMEOUT_CHAT=${LINEAGEWEAVE_CHAT_LLM_TIMEOUT:-60}
TIMEOUT_CONTENT=${LINEAGEWEAVE_CONTENT_LLM_TIMEOUT:-120}
WRITE_REPORTS="${LINEAGEWEAVE_WRITE_REPORTS:-1}"
SWEEP_CONTENT_INSPECTIONS="${LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS:-0}"
INSPECTION_DOCUMENT_LIMIT="${LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT:-0}"
VALIDATE_RUNTIME_SCHEMA="${LINEAGEWEAVE_VALIDATE_RUNTIME_SCHEMA:-1}"
runtime_schema_contract_check="disabled"
TEPP_OPEN_PULL_REQUESTS="$(query_open_pull_requests "ContextualWisdomLab/TEPP")"
ORCHESTRATOR_OPEN_PULL_REQUESTS="$(query_open_pull_requests "ContextualWisdomLab/contextual-orchestrator")"

redacted_dsn="$(python -c "import os, re; dsn = os.environ.get('LINEAGEWEAVE_DSN', ''); print(re.sub(r'//([^/]+)@', '//***:***@', dsn))")"
trap 'audit_exit_code=$?; emit_audit_json_line "lineageweave_real_run_exit" "source_dsn=$redacted_dsn" "source_table=$LINEAGE_SOURCE_TABLE" "write_reports=$WRITE_REPORTS" "keyman_limit=$KEYMAN_LIMIT" "limit=$LIMIT" "sweep_content_inspections=$SWEEP_CONTENT_INSPECTIONS" "inspection_document_limit=$INSPECTION_DOCUMENT_LIMIT" "validate_runtime_schema=$VALIDATE_RUNTIME_SCHEMA" "runtime_schema_contract_check=$runtime_schema_contract_check" "tepp_open_pull_requests=$TEPP_OPEN_PULL_REQUESTS" "contextual_orchestrator_open_pull_requests=$ORCHESTRATOR_OPEN_PULL_REQUESTS" "json_out=$json_out_audit" "analytics_out=$analytics_out_audit" "exit_code=$audit_exit_code" || true; exit "$audit_exit_code"' EXIT
echo "lineageweave_real_run_start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
emit_audit_json_line "lineageweave_real_run_start" \
  "source_dsn=$redacted_dsn" \
  "source_table=$LINEAGE_SOURCE_TABLE" \
  "write_reports=$WRITE_REPORTS" \
  "keyman_limit=$KEYMAN_LIMIT" \
  "limit=$LIMIT" \
  "sweep_content_inspections=$SWEEP_CONTENT_INSPECTIONS" \
  "inspection_document_limit=$INSPECTION_DOCUMENT_LIMIT" \
  "validate_runtime_schema=$VALIDATE_RUNTIME_SCHEMA" \
  "tepp_open_pull_requests=$TEPP_OPEN_PULL_REQUESTS" \
  "contextual_orchestrator_open_pull_requests=$ORCHESTRATOR_OPEN_PULL_REQUESTS" \
  "json_out=$json_out_audit" \
  "analytics_out=$analytics_out_audit"
echo "source_dsn=$redacted_dsn"
echo "source_table=$LINEAGE_SOURCE_TABLE"
echo "write_reports=$WRITE_REPORTS"
echo "keyman_limit=$KEYMAN_LIMIT"
echo "limit=$LIMIT"
echo "sweep_content_inspections=$SWEEP_CONTENT_INSPECTIONS"
echo "inspection_document_limit=$INSPECTION_DOCUMENT_LIMIT"
echo "validate_runtime_schema=$VALIDATE_RUNTIME_SCHEMA"
echo "tepp_open_pull_requests=$TEPP_OPEN_PULL_REQUESTS"
echo "contextual_orchestrator_open_pull_requests=$ORCHESTRATOR_OPEN_PULL_REQUESTS"
echo "json_out=$json_out_audit"
echo "analytics_out=$analytics_out_audit"

echo "lineageweave_real_plan=source=${LINEAGE_SOURCE_TABLE}; write_reports=${WRITE_REPORTS}; keyman_limit=${KEYMAN_LIMIT}; limit=${LIMIT}"

export LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT="$TIMEOUT_PRODUCT"
export LINEAGEWEAVE_KEYMAN_LLM_TIMEOUT="$TIMEOUT_KEYMAN"
export LINEAGEWEAVE_CHAT_LLM_TIMEOUT="$TIMEOUT_CHAT"
export LINEAGEWEAVE_CONTENT_LLM_TIMEOUT="$TIMEOUT_CONTENT"

limit_args=()
sweep_args=()
export_args=()
if [[ -n "$JSON_OUT" ]]; then
  export_args+=("--json-out" "$JSON_OUT")
fi
if [[ -n "$ANALYTICS_OUT" ]]; then
  export_args+=("--analytics-out" "$ANALYTICS_OUT")
fi
if [[ "$LIMIT" =~ ^[0-9]+$ ]] && [[ "$LIMIT" -gt 0 ]]; then
  limit_args+=("--limit" "$LIMIT")
elif [[ "$LIMIT" != "0" ]]; then
  echo "invalid LINEAGEWEAVE_LIMIT: must be a non-negative integer"
  exit 1
fi
if [[ "$SWEEP_CONTENT_INSPECTIONS" == "1" ]]; then
  sweep_args+=("--sweep-content-inspections")
  if [[ "$INSPECTION_DOCUMENT_LIMIT" != "0" ]]; then
    if [[ ! "$INSPECTION_DOCUMENT_LIMIT" =~ ^[0-9]+$ ]]; then
      echo "invalid LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT: must be a non-negative integer"
      exit 1
    fi
    sweep_args+=("--inspection-document-limit" "$INSPECTION_DOCUMENT_LIMIT")
  fi
fi

if [[ "$WRITE_REPORTS" == "0" ]]; then
  uv run python lineageweave.py \
    --dsn "$LINEAGEWEAVE_DSN" \
    --table "$LINEAGE_SOURCE_TABLE" \
    "${export_args[@]}" \
    --keyman-limit "$KEYMAN_LIMIT" \
    "${sweep_args[@]}" \
    "${limit_args[@]}"
else
  uv run python lineageweave.py \
    --dsn "$LINEAGEWEAVE_DSN" \
    --table "$LINEAGE_SOURCE_TABLE" \
    --write-reports \
    "${export_args[@]}" \
    --keyman-limit "$KEYMAN_LIMIT" \
    "${sweep_args[@]}" \
    "${limit_args[@]}"
fi

if [[ "$VALIDATE_RUNTIME_SCHEMA" != "0" ]]; then
  echo "runtime_schema_contract_check=enabled"
  runtime_schema_contract_check="enabled"
  uv run python scripts/check_runtime_schema_contract.py
else
  echo "runtime_schema_contract_check=disabled"
fi

printf 'lineageweave_real_run_complete=%s json=%s analytics=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$json_out_audit" "$analytics_out_audit"
echo "lineageweave_contract_check_status=$runtime_schema_contract_check"
emit_audit_json_line "lineageweave_real_run_complete" \
  "source_dsn=$redacted_dsn" \
  "source_table=$LINEAGE_SOURCE_TABLE" \
  "write_reports=$WRITE_REPORTS" \
  "keyman_limit=$KEYMAN_LIMIT" \
  "limit=$LIMIT" \
  "sweep_content_inspections=$SWEEP_CONTENT_INSPECTIONS" \
  "inspection_document_limit=$INSPECTION_DOCUMENT_LIMIT" \
  "validate_runtime_schema=$VALIDATE_RUNTIME_SCHEMA" \
  "runtime_schema_contract_check=$runtime_schema_contract_check" \
  "tepp_open_pull_requests=$TEPP_OPEN_PULL_REQUESTS" \
  "contextual_orchestrator_open_pull_requests=$ORCHESTRATOR_OPEN_PULL_REQUESTS" \
  "json_out=$json_out_audit" \
  "analytics_out=$analytics_out_audit"

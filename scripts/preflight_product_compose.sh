#!/usr/bin/env bash
set -euo pipefail

required_tools=(python docker)
for tool in "${required_tools[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "preflight failed: missing required tool: $tool" >&2
    exit 1
  fi
done

printf 'preflight-product-compose=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Keep compose identity boundary hardening explicit and non-overridable.
python scripts/check_compose_identity_boundary.py

if ! missing_product_settings="$(docker compose --profile product config --format json | python -c '
import json
import sys

config = json.load(sys.stdin)
service = config.get("services", {}).get("lineageweave", {})
environment = service.get("environment")
if not isinstance(environment, dict):
    raise SystemExit(2)
required = (
    "LINEAGEWEAVE_DSN",
    "LINEAGE_SOURCE_TABLE",
    "KEYVERSE_ISSUER",
    "LINEAGEWEAVE_OIDC_CLIENT_ID",
    "LINEAGEWEAVE_OIDC_CLIENT_SECRET",
    "LINEAGEWEAVE_OIDC_REDIRECT_URI",
)
print(",".join(name for name in required if not str(environment.get(name) or "").strip()))
')"; then
  echo "preflight failed: unable to resolve product compose configuration" >&2
  exit 1
fi

if [[ -n "$missing_product_settings" ]]; then
  echo "preflight failed: product configuration is missing required direct-PostgreSQL or Keyverse settings: $missing_product_settings" >&2
  exit 1
fi

echo "preflight-product-compose-ok"

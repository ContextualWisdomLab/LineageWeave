.PHONY: up down logs smoke seed ps load-http load-mcp

# Compose reads the repository-local .env convention when present. Provider
# credentials belong to the separately deployed contextual-orchestrator and
# are not an input to the LineageWeave stack.
COMPOSE := docker compose

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# Machine-to-machine OIDC boundary probe against the running Keycloak realm.
# Browser login acceptance lives in the Playwright product path; this target
# verifies the synthetic test-automation client's signed API-audience token.
smoke:
	@test -n "$${KEYCLOAK_CLIENT_SECRET:-}" || { echo "KEYCLOAK_CLIENT_SECRET is required" >&2; exit 1; }
	uv run --locked --extra dev python scripts/smoke_test_oidc.py

# Seeds synthetic corp/account/post rows keyed to the actual Keycloak demo
# users' real subject ids, plus Valkey ticket_created events so Activity
# is not empty (see scripts/seed_demo_data.py). The second command binds the
# realm's deterministic confidential service-account subjects to the same
# DB-owned affiliation/role model; it does not authenticate to Keycloak.
seed:
	@test -n "$${KEYCLOAK_ADMIN_PASSWORD:-}" || { echo "KEYCLOAK_ADMIN_PASSWORD is required" >&2; exit 1; }; \
	uv run --locked --extra dev --extra backend python scripts/seed_demo_data.py; \
	uv run --locked --extra dev --extra backend python scripts/provision_local_service_accounts.py

# Authenticated Compose measurement with no invented pass/fail threshold.
# The operator must supply a representative concurrency and observation window.
load-http:
	@test -n "$${LINEAGEWEAVE_VUS:-}" || { echo "LINEAGEWEAVE_VUS is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_DURATION:-}" || { echo "LINEAGEWEAVE_DURATION is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_REQUEST_TIMEOUT:-}" || { echo "LINEAGEWEAVE_REQUEST_TIMEOUT is required" >&2; exit 1; }
	@test -n "$${KEYCLOAK_CLIENT_SECRET:-}" || { echo "KEYCLOAK_CLIENT_SECRET is required" >&2; exit 1; }
	k6 run -e REQUEST_TIMEOUT="$${LINEAGEWEAVE_REQUEST_TIMEOUT}" --vus "$${LINEAGEWEAVE_VUS}" --duration "$${LINEAGEWEAVE_DURATION}" scripts/k6_http_e2e.js

# Authenticated MCP measurement with operator-supplied observation bounds.
load-mcp:
	@test -n "$${LINEAGEWEAVE_VUS:-}" || { echo "LINEAGEWEAVE_VUS is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_DURATION:-}" || { echo "LINEAGEWEAVE_DURATION is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_REQUEST_TIMEOUT:-}" || { echo "LINEAGEWEAVE_REQUEST_TIMEOUT is required" >&2; exit 1; }
	@test -n "$${KEYCLOAK_CLIENT_SECRET:-}" || { echo "KEYCLOAK_CLIENT_SECRET is required" >&2; exit 1; }
	k6 run -e REQUEST_TIMEOUT="$${LINEAGEWEAVE_REQUEST_TIMEOUT}" --vus "$${LINEAGEWEAVE_VUS}" --duration "$${LINEAGEWEAVE_DURATION}" scripts/k6_mcp_e2e.js
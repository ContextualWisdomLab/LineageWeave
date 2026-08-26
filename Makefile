.PHONY: up down logs smoke seed ps load-http load-mcp

# Keep provider credentials outside the repository. Compose interpolation must
# read the same home env file as the orchestrator container's env_file.
COMPOSE := docker compose --env-file "$$HOME/.env"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# Real OIDC round-trip against the running Keycloak container: logs in as
# the synthetic demo user, verifies the returned JWT's signature against
# Keycloak's live JWKS, and asserts the corp_code/pu_code claims. See
# scripts/smoke_test_oidc.py.
smoke:
	uv run --locked --extra dev python scripts/smoke_test_oidc.py

# Seeds synthetic corp/account/post rows keyed to the actual Keycloak demo
# users' real subject ids, plus Valkey ticket_created events so Activity
# is not empty (see scripts/seed_demo_data.py). Run after `up`.
seed:
	@test -n "$${KEYCLOAK_ADMIN_PASSWORD:-}" || { echo "KEYCLOAK_ADMIN_PASSWORD is required" >&2; exit 1; }; \
	uv run --locked python scripts/seed_demo_data.py

# Authenticated Compose measurement with no invented pass/fail threshold.
# The operator must supply a representative concurrency and observation window.
load-http:
	@test -n "$${LINEAGEWEAVE_VUS:-}" || { echo "LINEAGEWEAVE_VUS is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_DURATION:-}" || { echo "LINEAGEWEAVE_DURATION is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_REQUEST_TIMEOUT:-}" || { echo "LINEAGEWEAVE_REQUEST_TIMEOUT is required" >&2; exit 1; }
	k6 run -e REQUEST_TIMEOUT="$${LINEAGEWEAVE_REQUEST_TIMEOUT}" --vus "$${LINEAGEWEAVE_VUS}" --duration "$${LINEAGEWEAVE_DURATION}" scripts/k6_http_e2e.js

# Authenticated MCP measurement with operator-supplied observation bounds.
load-mcp:
	@test -n "$${LINEAGEWEAVE_VUS:-}" || { echo "LINEAGEWEAVE_VUS is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_DURATION:-}" || { echo "LINEAGEWEAVE_DURATION is required" >&2; exit 1; }
	@test -n "$${LINEAGEWEAVE_REQUEST_TIMEOUT:-}" || { echo "LINEAGEWEAVE_REQUEST_TIMEOUT is required" >&2; exit 1; }
	k6 run -e REQUEST_TIMEOUT="$${LINEAGEWEAVE_REQUEST_TIMEOUT}" --vus "$${LINEAGEWEAVE_VUS}" --duration "$${LINEAGEWEAVE_DURATION}" scripts/k6_mcp_e2e.js

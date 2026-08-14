.PHONY: up down logs smoke seed ps

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

# Real OIDC round-trip against the running Keycloak container: logs in as
# the synthetic demo user, verifies the returned JWT's signature against
# Keycloak's live JWKS, and asserts the corp_code/pu_code claims. See
# scripts/smoke_test_oidc.py.
smoke:
	python3 scripts/smoke_test_oidc.py

# Seeds synthetic corp/account/post rows keyed to the actual Keycloak demo
# users' real subject ids, plus Valkey ticket_created events so Activity
# is not empty (see scripts/seed_demo_data.py). Run after `up`.
seed:
	@test -n "$${KEYCLOAK_ADMIN_PASSWORD:-}" || { echo "KEYCLOAK_ADMIN_PASSWORD is required" >&2; exit 1; }; \
	python3 scripts/seed_demo_data.py

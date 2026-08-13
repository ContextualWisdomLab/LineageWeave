.PHONY: up down logs smoke ps

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

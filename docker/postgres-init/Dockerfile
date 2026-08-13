FROM postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777
# Build context is the repo root (see docker-compose.yml) so both the
# Keycloak-database bootstrap and the product schema can be copied from
# their single sources of truth.
COPY docker/postgres-init/01-create-keycloak-db.sql /docker-entrypoint-initdb.d/01-create-keycloak-db.sql
# The exact same migration file tests/test_schema.py applies -- single
# source of truth, no re-typed copy. Runs against POSTGRES_DB (the "app"
# database) because docker-entrypoint-initdb.d executes each *.sql file
# with that database already selected.
COPY migrations/0001_initial_schema.sql /docker-entrypoint-initdb.d/02-app-schema.sql
COPY migrations/0002_thread_grouping_keys.sql /docker-entrypoint-initdb.d/03-thread-grouping-keys.sql
# Official image already drops to this account at runtime; declare it so
# the Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER postgres

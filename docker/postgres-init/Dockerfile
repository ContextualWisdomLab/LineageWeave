FROM postgres:16-alpine
COPY docker/postgres-init/01-create-keycloak-db.sql /docker-entrypoint-initdb.d/01-create-keycloak-db.sql
# The exact same migration file tests/test_schema.py applies -- single
# source of truth, no re-typed copy. Runs against POSTGRES_DB (the "app"
# database) because docker-entrypoint-initdb.d executes each *.sql file
# with that database already selected.
COPY migrations/0001_initial_schema.sql /docker-entrypoint-initdb.d/02-app-schema.sql

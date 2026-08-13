FROM postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777
COPY 01-create-keycloak-db.sql /docker-entrypoint-initdb.d/01-create-keycloak-db.sql
# Official image already drops to this account at runtime; declare it so
# the Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER postgres

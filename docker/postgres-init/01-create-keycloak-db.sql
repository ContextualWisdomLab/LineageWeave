-- Keycloak stores its own realm/session state in a separate database on the
-- same PostgreSQL instance (one running database service, not a second file
-- DB) so the stack stays "PostgreSQL only" per ARCHITECTURE.md.
CREATE DATABASE keycloak;

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
COPY migrations/0003_ticket_commitment_calendar.sql /docker-entrypoint-initdb.d/04-ticket-commitment-calendar.sql
COPY migrations/0004_relation_verification.sql /docker-entrypoint-initdb.d/05-relation-verification.sql
COPY migrations/0005_post_evaluation.sql /docker-entrypoint-initdb.d/06-post-evaluation.sql
COPY migrations/0006_report_period_score.sql /docker-entrypoint-initdb.d/07-report-period-score.sql
COPY migrations/0007_report_fipc_linking.sql /docker-entrypoint-initdb.d/08-report-fipc-linking.sql
COPY migrations/0008_post_summary_result.sql /docker-entrypoint-initdb.d/09-post-summary-result.sql
COPY migrations/0009_shared_metric_bank.sql /docker-entrypoint-initdb.d/10-shared-metric-bank.sql
COPY migrations/0010_report_item_information.sql /docker-entrypoint-initdb.d/11-report-item-information.sql
COPY migrations/0011_post_chat_result.sql /docker-entrypoint-initdb.d/12-post-chat-result.sql
COPY migrations/0012_report_leftover_pair.sql /docker-entrypoint-initdb.d/13-report-leftover-pair.sql
COPY migrations/0013_activity_outbox.sql /docker-entrypoint-initdb.d/14-activity-outbox.sql
# Official image already drops to this account at runtime; declare it so
# the Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER postgres

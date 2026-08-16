FROM postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777
# Build context is the repo root (see docker-compose.yml) so both the
# Keycloak-database bootstrap and the product schema can be copied from
# their single sources of truth.
COPY docker/postgres-init/01-create-keycloak-db.sql /docker-entrypoint-initdb.d/01-create-keycloak-db.sql
# The exact same migration files the PostgreSQL contract tests apply -- single
# source of truth, no re-typed copy. docker-entrypoint-initdb.d executes each
# file against POSTGRES_DB in lexical order.
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
COPY migrations/0012_role_responsibility_agent_type.sql /docker-entrypoint-initdb.d/13-role-responsibility-agent-type.sql
COPY migrations/0013_person_job_title.sql /docker-entrypoint-initdb.d/14-person-job-title.sql
COPY migrations/0014_role_responsibility_team_actor_type.sql /docker-entrypoint-initdb.d/15-role-responsibility-team-actor-type.sql
COPY migrations/0015_organization_name_resolution.sql /docker-entrypoint-initdb.d/16-organization-name-resolution.sql
COPY migrations/0016_cross_post_actor_identity.sql /docker-entrypoint-initdb.d/17-cross-post-actor-identity.sql
COPY migrations/0017_prov_o_standard_relations.sql /docker-entrypoint-initdb.d/18-prov-o-standard-relations.sql
COPY migrations/0018_analysis_run_registry.sql /docker-entrypoint-initdb.d/19-analysis-run-registry.sql
COPY migrations/0019_role_catalog_identity.sql /docker-entrypoint-initdb.d/20-role-catalog-identity.sql
COPY migrations/0020_analysis_run_retention_purge.sql /docker-entrypoint-initdb.d/21-analysis-run-retention-purge.sql
COPY migrations/0021_analysis_run_reconstruction.sql /docker-entrypoint-initdb.d/22-analysis-run-reconstruction.sql
COPY migrations/0022_analysis_source_snapshot_member.sql /docker-entrypoint-initdb.d/23-analysis-source-snapshot-member.sql
COPY migrations/0023_analysis_run_retention_purge_reconstruction.sql /docker-entrypoint-initdb.d/24-analysis-run-retention-purge-reconstruction.sql
# Official image already drops to this account at runtime; declare it so
# the Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER postgres

# Normalized Analysis-Run Registry Design

**Status:** Approved implementation design on an active stacked PR  
**Parent:** LineageWeave PR #74 exact head `2ace79ea90a82d61f8467bbe644dd23b0deaa8b6`  
**Issue:** #79, Milestone 2 additive direct-PostgreSQL port

## Goal

Add the smallest durable PostgreSQL contract needed to identify and audit LineageWeave analysis runs without importing the closed prototype's parallel application, denormalized run row, raw data, or service-owned computation.

## Product boundary

LineageWeave owns product-visible run identity, source-snapshot identity, authorization scope, idempotency, and state history. Existing product relations remain authoritative for posts, lineage, entities, reports, and provenance. TEPP owns temporal/psychometric estimation. contextual-orchestrator owns model routing and model-provider execution. Valkey carries events but does not become durable run truth.

## Data design

The design uses five relations:

- `analysis_source_snapshot`: immutable digest and temporal knowledge boundary;
- `analysis_source_count`: normalized aggregate reconciliation values;
- `analysis_run`: idempotent request and reproducibility digests;
- `analysis_run_scope`: at most one optional, mutually exclusive product scope; the later creation repository inserts the required scope atomically;
- `analysis_run_status_event`: append-only state history.

The `analysis_run_current_status` view returns the highest ordinal event for each run. No JSON payload is persisted. Optional model and prompt hashes remain null for deterministic runs.

## Security and privacy

The public schema stores no raw record, source-table name, source identifier, image, credential, provider payload, or raw exception. `requested_by_account_id` references the real OIDC-backed product account. Scope references existing corporate/process-unit identities or a bounded thread key; it does not trust token claims as database truth. Future API access reuses current RBAC/ABAC until a separate accepted RLS decision exists.

## Failure behavior

- malformed digests, unsupported enum codes, negative counts, duplicate idempotency keys, and incoherent scope shapes fail in PostgreSQL;
- failed status events require a bounded machine failure code;
- non-failed events cannot carry failure/retry metadata;
- update/delete of status events raises a stable database error;
- lookup-code category collisions abort migration;
- rollback refuses any non-empty registry relation.

## Deployment

The product PostgreSQL image applies migration 0018 after migration 0017. No new service or container is introduced. A later API/outbox slice may use these relations but cannot claim implementation from this schema alone.

## Testing

Static tests run without external services and lock file names, table names, normalization, lookup inventory, Docker migration order, and fail-closed rollback markers. Real PostgreSQL tests use the committed migration files, generated quoted database identifiers, preserved DSN query options, and actual database exceptions. Hosted exact-head CI remains authoritative for the PostgreSQL lane.

## Deferred work

API repository methods, Valkey outbox persistence, TEPP submission, contextual-orchestrator task envelopes, React/Storybook surfaces, RLS, signed acceptance manifests, artifact registries, and retention tooling are separate reviewable slices.

# Analysis-run registry implementation plan

> Execute test-first. Preserve the reviewed LineageWeave product and keep
> private actual-data evidence outside public source control.

**Goal:** Establish one normalized, temporally truthful, actor-scoped registry
for Milestone 2 analysis requests and lifecycle evidence.

## Task 1 — RED: database contract

**File:** `tests/test_analysis_run_registry_schema.py`

1. Require the five normalized relations, current-status view, rollback, and
   fresh-install wiring.
2. Reject the retained experiment's denormalized table and JSON metadata.
3. Require evidence-owned availability/capture clocks and a run-owned cutoff.
4. Require non-null requester identity and account-scoped idempotency.
5. Require immutable snapshot, count, and run request rows.
6. Require shared row locking between count mutation and first run creation.
7. Require pending-first, contiguous, monotonic, legal status transitions and
   append-only status rows.
8. Require fail-closed rollback and descriptive database-object names.

## Task 2 — GREEN: normalized migration and rollback

**Files:**

- `migrations/0018_analysis_run_registry.sql`
- `migrations/rollback/0018_analysis_run_registry.sql`
- `docker/postgres-init/Dockerfile`

1. Insert category-checked lookup values idempotently.
2. Add snapshot, count, run, scope, and status-event relations in 3NF.
3. Keep `maximum_available_time` on the snapshot and `knowledge_cutoff` on the
   run.
4. Serialize count freeze and run creation through the same snapshot row lock.
5. Reject mutation of immutable evidence and request configuration.
6. Implement the lifecycle state machine as a serialized insert trigger.
7. Add the current-status read view.
8. Refuse rollback while any audit evidence exists.
9. Apply migration 0018 after the PROV-O migration on fresh PostgreSQL images.

## Task 3 — Documentation and evidence

**Files:**

- `docs/adr/0013-normalized-analysis-run-registry.md`
- `docs/doctoring/ANALYSIS_RUN_REGISTRY_REFERENCES.md`
- `CHANGELOG.d/milestone2-analysis-run-registry.md`

1. Record product/service ownership and deferred API/UI claims.
2. Trace temporal, provenance, audit, privacy, concurrency, and rollback
   decisions to current authoritative sources in APA 7th form.
3. Mark active-PR decisions as non-main truth.
4. Keep public fixtures synthetic and exclude private source identifiers.

## Task 4 — Exact-head verification

1. Run the static test without PostgreSQL and prove it fails before migration.
2. Run all registry cases against real PostgreSQL after implementation.
3. Replay the migration and rollback.
4. Run the complete Python product suite against PostgreSQL.
5. Run frontend lint, complete tests, and production build.
6. Run `compileall`, security, SAST, documentation hygiene, and public-content
   scans.
7. Inspect the exact final diff for temporary workflows/scripts.
8. Obtain independent exact-head review and merge only after the parent PR is on
   protected `main` and base-sensitive evidence is regenerated.

## Task 5 — Knowledge-cutoff post projection (v0.83.0)

1. Fail if a post written after `knowledge_cutoff` appears in
   `visible_posts`.
2. Apply `created_at <= knowledge_cutoff` in the authorized read.
3. Show revision/config digest prefixes on the home detail.
4. Extract `AnalysisRunsPanel` and inventory Storybook states.

## Task 6 — Next bounded vertical slice

After this registry reaches protected main:

1. Write failing repository tests for atomic run + scope + pending-event
   creation and idempotent request comparison.
2. Implement the async PostgreSQL repository with no cross-service SQL.
3. Add RBAC/ABAC-protected source-redacting list/detail endpoints.
4. Add the DB-grounded read-only administrator surface and Storybook states.
5. Add normalized outbox + Valkey delivery.
6. Integrate TEPP and contextual-orchestrator only through reviewed versioned
   contracts.
7. Execute private actual-data analysis and retain signed aggregate acceptance
   artifacts outside public Git history.

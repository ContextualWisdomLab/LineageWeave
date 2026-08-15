# Normalized Analysis-Run Registry Implementation Plan

> Execute test-first. Preserve the protected LineageWeave product and port only
> bounded evidence from the retained Milestone 2 experiment.

**Goal:** Add a normalized, fail-closed PostgreSQL registry for reusable source
captures and account-owned analysis runs without copying the parallel product.

**Architecture:** Sequential migration 0018 adds snapshot, aggregate-count, run,
scope, and append-only status relations plus a derived current-status view.
`maximum_available_time` and `captured_at` belong to the reusable snapshot;
`knowledge_cutoff` belongs to each run. Existing identity, product data,
lineage, report, provenance, TEPP, contextual-orchestrator, and Valkey boundaries
remain unchanged.

**Tech stack:** PostgreSQL 16-compatible SQL, Python 3.12+, pytest, psycopg2, and
the digest-pinned official PostgreSQL image.

## Global constraints

- Start from PR #74 exact head `2ace79ea90a82d61f8467bbe644dd23b0deaa8b6`.
- Keep source data, organization-specific names, source-table identifiers,
  base64 payloads, credentials, provider payloads, and raw exceptions out of
  public Git and registry rows.
- Use descriptive two-or-more-word `snake_case` database objects and 3NF.
- Do not add a second React app, Keyverse-shaped identity service, TEPP
  arithmetic, or cross-service SQL.
- Fail closed on PostgreSQL contract violations and refuse destructive rollback
  while audit evidence exists.
- Exact-head hosted PostgreSQL, security, SAST, and review gates become
  authoritative after the stack is refreshed onto protected `main`.

## Task 1 — RED: normalized registry and temporal ownership

**File:** `tests/test_analysis_run_registry_schema.py`

- Require the five normalized relations and current-status view.
- Reject the legacy denormalized table and JSON metadata.
- Require reusable snapshot clocks (`maximum_available_time`, `captured_at`) and
  run-owned `knowledge_cutoff`.
- Require non-null requesting account and account-scoped idempotency.
- Use quoted generated database identifiers and preserve DSN query options.
- Prove static RED before migration implementation.

## Task 2 — RED: immutable evidence and lifecycle

**File:** `tests/test_analysis_run_registry_schema.py`

- Prove one snapshot supports multiple later run cutoffs.
- Reject source evidence later than the run cutoff.
- Reject snapshot/count mutation and count insert/delete after first run.
- Reject missing actor and same-account idempotency reuse while allowing the
  same key for another account.
- Reject incoherent scopes and incomplete failure events.
- Reject non-pending first state, ordinal gaps, direct pending-to-success,
  reversed occurrence time, and transitions after terminal state.

## Task 3 — GREEN: migration and rollback

**Files:**

- `migrations/0018_analysis_run_registry.sql`
- `migrations/rollback/0018_analysis_run_registry.sql`
- `docker/postgres-init/Dockerfile`

Implementation requirements:

1. Register bounded lookup codes and reject lookup-category collision.
2. Add snapshot, count, run, scope, status, and current-status view.
3. Lock the snapshot on count-set changes and run creation.
4. Enforce `maximum_available_time <= knowledge_cutoff` per run.
5. Freeze snapshot/count/run/scope evidence as appropriate.
6. Serialize status appends and validate the complete history after each insert
   statement, including multi-row inserts.
7. Make status updates/deletes fail closed.
8. Make migration replay-safe and rollback refuse non-empty evidence.
9. Apply migration 0018 after PROV-O migration 0017 in fresh containers.

## Task 4 — Architecture and research truth

**Files:**

- `docs/adr/0013-normalized-analysis-run-registry.md`
- `docs/superpowers/specs/2026-08-15-analysis-run-registry-design.md`
- `docs/doctoring/ANALYSIS_RUN_REGISTRY_REFERENCES.md`
- `CHANGELOG.d/0.79.0-analysis-run-registry.md`

Document exact ownership, temporal semantics, concurrency locks, lifecycle,
privacy exclusions, rollback, deferred API/UI/service adapters, maturity, and
APA 7 references. Do not present active-PR behavior as protected-main truth.

## Task 5 — Verification and stack integration

1. Run static contract locally; do not count skipped PostgreSQL tests as passing.
2. Run all real PostgreSQL cases on hosted CI with a required reachable service.
3. Run full Python, frontend lint/test/build, documentation hygiene, security,
   SAST, and public-content scans on the exact refreshed head.
4. Keep the PR Draft while #74 is open.
5. After #74 merges, rebuild or retarget the bounded delta on exact protected
   `main`; prior-base checks and reviews do not transfer.
6. Obtain independent current-head approval and merge only through the live
   protected policy.
7. Continue with the atomic repository/API/outbox slice; do not duplicate
   migration 0018 or ADR 0013.

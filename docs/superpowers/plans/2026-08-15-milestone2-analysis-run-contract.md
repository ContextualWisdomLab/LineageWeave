# Milestone 2 analysis-run contract implementation plan

> Execute with test-driven development. Do not copy the retained parallel
> product branch wholesale. Preserve private actual-data evidence outside
> public source control.

**Goal:** Add a normalized, source-redacting provenance root for direct
PostgreSQL product analysis and downstream TEPP/orchestrator/fast-mlsirm calls.

**Base:** Stack additively after the protected PROV-O and related-person label
line. Retarget to `main` only after its ancestors merge.

## Task 1 — Pure evidence contracts

**Files**

- Create `lineageweave/analysis_run.py`
- Create `tests/test_analysis_run.py`

**Steps**

1. Write failing tests for exact UTF-8 hashing and deterministic canonical JSON
   hashing.
2. Write failing profile validation tests for opaque keys, revisions, source
   kinds, and lowercase SHA-256.
3. Write failing snapshot tests for aware timestamps,
   `maximum_available_time <= knowledge_cutoff`, nonnegative counts, and
   `thread_count <= document_count <= row_count`.
4. Write failing configuration and lifecycle tests.
5. Implement the smallest contract that passes.
6. Require 100% statement and branch coverage.

## Task 2 — Transaction repository

**Files**

- Create `backend/app/analysis_run_ingestion.py`
- Create `backend/tests/test_analysis_run_ingestion.py`

**Steps**

1. Write a deterministic asynchronous fake connection and transaction.
2. Prove registration writes profile, snapshot, run, configuration, and start
   event inside one transaction.
3. Prove profile, snapshot, and idempotency conflicts fail closed.
4. Prove successful and failed terminal transitions append the correct event.
5. Prove the list projection omits private source channels and bounds its limit.
6. Implement the repository through a minimal structural connection protocol.
7. Require 100% statement and branch coverage.

## Task 3 — PostgreSQL migration

**Files**

- Create `migrations/0018_analysis_run_provenance.sql`
- Create `tests/test_analysis_run_schema.py`
- Modify `docker/postgres-init/Dockerfile`

**Steps**

1. Write a real-PostgreSQL test that applies `0001` then `0018`.
2. Prove a normalized source profile, snapshot, run, configuration, service
   call, and artifact can be inserted.
3. Prove future-information leakage is rejected by a check constraint.
4. Prove duplicate profile revisions and malformed digests are rejected.
5. Prove every created table has two or more `snake_case` words.
6. Add lookup values, tables, FKs, checks, unique constraints, and indexes.
7. Wire `0018` into fresh Docker initialization.

## Task 4 — Architecture and research traceability

**Files**

- Create `docs/adr/0013-analysis-run-provenance-boundary.md`
- Create this plan and the paired design specification
- Create `docs/doctoring/ANALYSIS_RUN_PROVENANCE_REFERENCES.md`
- Create `CHANGELOG.d/milestone2-analysis-run-contract.md`

**Steps**

1. Record LineageWeave, TEPP, contextual-orchestrator, and fast-mlsirm ownership.
2. Document why SQL, DSNs, raw content, and private source identifiers are never
   persisted in the run contract.
3. Trace PROV-O, OWL-Time, OpenAPI, and the accepted TEPP baseline in APA 7th
   form.
4. Document private acceptance-manifest handling and public-content scanning.

## Task 5 — Verification and merge sequencing

1. Run focused tests and 100% branch coverage for both new production modules.
2. Run `compileall` and `git diff --check`.
3. Scan the complete diff for prohibited private source identifiers, SQL, DSNs,
   credentials, temporary workflows, and repair scripts.
4. Open a Draft stacked PR; do not mark ready while an ancestor PR is open.
5. After ancestors merge, retarget or rebuild onto current `main`.
6. Run complete Python/PostgreSQL/frontend/build/security/SAST gates on the
   exact head.
7. Obtain independent current-head approval and merge only through protected
   auto-merge.
8. Continue with the authenticated run-status API/UI and actual execution slice.

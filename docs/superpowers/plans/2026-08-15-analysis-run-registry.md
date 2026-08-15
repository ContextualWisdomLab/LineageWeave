# Normalized Analysis-Run Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a normalized, fail-closed PostgreSQL registry for Milestone 2 source snapshots and analysis runs without copying the closed prototype application.

**Architecture:** A sequential migration adds snapshot, aggregate-count, run, scope, and append-only status relations plus a derived current-status view. Existing identity, product data, lineage, report, provenance, TEPP, contextual-orchestrator, and Valkey boundaries remain unchanged.

**Tech Stack:** PostgreSQL 16-compatible SQL, Python 3.12+, pytest, psycopg2, Docker official PostgreSQL image.

## Global Constraints

- Start from PR #74 exact head `2ace79ea90a82d61f8467bbe644dd23b0deaa8b6`.
- No source data, organization-specific names, source-table identifiers, base64 payloads, credentials, or raw exceptions in public Git or registry rows.
- All database objects use descriptive two-or-more-word snake_case and remain third-normalized.
- Do not add a second React application, Keyverse-shaped local identity service, TEPP arithmetic, or cross-service table access.
- PostgreSQL failures are fail-closed; rollback must not destroy non-empty audit evidence.
- Exact-head hosted PostgreSQL and security gates are authoritative after the stack is refreshed onto protected main.

---

### Task 1: Lock the missing normalized registry contract

**Files:**
- Create: `tests/test_analysis_run_registry_schema.py`

**Interfaces:**
- Consumes: `migrations/0001_initial_schema.sql`, the PostgreSQL administrator DSN.
- Produces: executable expectations for migration `0018`, rollback, Docker ordering, relational integrity, and append-only status.

- [ ] **Step 1: Write the static and real-database regression tests**

Add tests that require the five normalized relations and view, reject the legacy denormalized table/JSON payload, create a throwaway database with `psycopg2.sql.Identifier`, preserve DSN query parameters, and exercise success/failure/rollback contracts.

- [ ] **Step 2: Run the focused suite and observe RED**

Run:

```bash
python -m pytest -q tests/test_analysis_run_registry_schema.py
```

Expected: the static contract fails because migration `0018_analysis_run_registry.sql` does not exist. In environments without PostgreSQL, real-database cases skip while the static RED remains.

- [ ] **Step 3: Commit the RED contract only when repository policy permits a test-only checkpoint**

```bash
git add tests/test_analysis_run_registry_schema.py
git commit -m "test: require normalized analysis run registry"
```

### Task 2: Implement migration, downgrade, and image ordering

**Files:**
- Create: `migrations/0018_analysis_run_registry.sql`
- Create: `migrations/rollback/0018_analysis_run_registry.sql`
- Modify: `docker/postgres-init/Dockerfile`

**Interfaces:**
- Consumes: `common_lookup_value`, `user_account`, `corporate_entity`, `process_unit`, `uuid_generate_v4()`.
- Produces: `analysis_source_snapshot`, `analysis_source_count`, `analysis_run`, `analysis_run_scope`, `analysis_run_status_event`, `analysis_run_current_status`.

- [ ] **Step 1: Add the minimal normalized relations**

Implement explicit lookup codes, SHA/time/scope/status checks, indexes for current product queries, and comments that define exclusions.

- [ ] **Step 2: Make status history append-only**

Add a trigger function that raises `analysis_run_status_event_is_append_only` on update/delete. Keep current status as a view over the highest ordinal.

- [ ] **Step 3: Add a fail-closed downgrade**

The rollback checks every relation and raises `analysis_run_registry_not_empty` before dropping any object. Empty rollback drops the view, tables, trigger function, and only the migration-owned lookup codes.

- [ ] **Step 4: Add migration 0018 to the PostgreSQL image**

Copy it as `/docker-entrypoint-initdb.d/19-analysis-run-registry.sql` after PROV-O migration 0017.

- [ ] **Step 5: Run focused GREEN verification**

```bash
python -m pytest -q tests/test_analysis_run_registry_schema.py
```

Expected locally without PostgreSQL: static test passes and real database cases skip for one explicit service-unavailable reason. Expected in hosted CI: all static and real PostgreSQL cases pass.

- [ ] **Step 6: Run repository validation**

```bash
uv run --frozen python -m pytest -q
uv run --frozen python -m compileall -q lineageweave backend tests
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
git diff --check
```

### Task 3: Record architecture, research, and release truth

**Files:**
- Create: `docs/adr/0013-normalized-analysis-run-registry.md`
- Create: `docs/superpowers/specs/2026-08-15-analysis-run-registry-design.md`
- Create: `docs/doctoring/ANALYSIS_RUN_REGISTRY_REFERENCES.md`
- Create: `CHANGELOG.d/0.78.0-analysis-run-registry.md`

**Interfaces:**
- Consumes: Issue #79, ADRs 0001–0012, current PostgreSQL/PROV/ISO sources.
- Produces: durable ownership, data, failure, rollback, testing, and follow-up contracts.

- [ ] **Step 1: Record the accepted additive-boundary decision**

Explain why the prototype table and second app are rejected; include a Mermaid ERD and exact deferred API/outbox/UI work.

- [ ] **Step 2: Record APA 7 references and maturity**

Cite current PostgreSQL 18 constraints documentation, current ISO 8601-1:2019 status, and W3C PROV-O. Mark behavior as active-PR until protected integration.

- [ ] **Step 3: Add the changelog fragment**

Describe normalized evidence, append-only status, fail-closed rollback, and excluded raw/source/provider data without claiming an API exists.

- [ ] **Step 4: Run documentation hygiene**

```bash
python -m pytest -q tests/test_documentation_hygiene.py
python -m pytest -q tests/test_analysis_run_registry_schema.py::test_registry_contract_files_are_present_and_normalized
git diff --check
```

### Task 4: Publish one dependency-ordered stacked PR

**Files:**
- No additional product files.

**Interfaces:**
- Consumes: exact parent head and completed verification evidence.
- Produces: one bounded Draft PR targeting `feat/role-responsibility-agent-ontology`.

- [ ] **Step 1: Refetch parent and branch identity**

Abort or rebuild if PR #74 head is no longer `2ace79ea90a82d61f8467bbe644dd23b0deaa8b6`.

- [ ] **Step 2: Push the reviewed commit without rewriting history**

Create `feat/analysis-run-registry-v079` from the exact parent and push ordinary commits only.

- [ ] **Step 3: Open a Draft stacked PR**

State that parent checks/reviews do not transfer, real PostgreSQL hosted evidence is pending, and no API/UI/TEPP execution is claimed.

- [ ] **Step 4: Request current-head semantic review**

Request CodeRabbit/OpenCode on the exact head, fix only verified findings test-first, and keep the PR Draft until parent integration plus refreshed main-base checks.

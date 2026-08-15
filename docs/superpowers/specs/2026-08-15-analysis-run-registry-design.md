# Normalized Analysis-Run Registry Design

**Status:** Approved implementation design on an active stacked PR  
**Parent:** LineageWeave PR #74 exact head `2ace79ea90a82d61f8467bbe644dd23b0deaa8b6`  
**Issue:** #79, Milestone 2 additive direct-PostgreSQL port

## Goal

Add the smallest durable PostgreSQL contract needed to identify and audit
LineageWeave analysis runs without importing the retained experiment's parallel
application, denormalized run row, raw data, or service-owned computation.

## Product boundary

LineageWeave owns product-visible run identity, source-capture identity,
authorization scope, actor-scoped idempotency, and state history. Existing
product relations remain authoritative for posts, lineage, entities, reports,
and provenance. TEPP owns temporal and psychometric estimation.
contextual-orchestrator owns model routing and provider execution. Valkey carries
events but does not become durable run truth.

## Data design

The design uses five relations:

- `analysis_source_snapshot`: immutable capture digest, source-contract revision,
  latest evidence-availability time, and capture time;
- `analysis_source_count`: normalized aggregate reconciliation values;
- `analysis_run`: immutable account-owned request, run-specific knowledge cutoff,
  and reproducibility digests;
- `analysis_run_scope`: at most one mutually exclusive product scope; the later
  creation repository inserts the required scope atomically;
- `analysis_run_status_event`: append-only, ordered lifecycle history.

The `analysis_run_current_status` view returns the highest ordinal event for each
run. No JSON payload is persisted. Optional model and prompt hashes remain null
for deterministic runs.

## Temporal and concurrency contract

A source capture is reusable across analysis occasions, so `knowledge_cutoff`
belongs to the run rather than the snapshot. PostgreSQL locks the snapshot on
run creation and rejects:

```text
maximum_available_time > knowledge_cutoff
```

Snapshot and count rows reject updates. Count insert/delete and run creation
lock the same snapshot row, closing the race between changing aggregate evidence
and starting the first derivation. Once a run references the snapshot, the count
set is frozen.

## Identity and idempotency

Every run references a real OIDC-backed `user_account`. Idempotency is unique on
`(requested_by_account_id, idempotency_key)`, allowing different authenticated
actors to use the same opaque key while preventing one actor from creating two
requests with it.

## Lifecycle contract

Status history is a serialized state machine:

```text
pending -> running -> succeeded | failed | cancelled
pending -> failed | cancelled
```

The first status is pending at ordinal 1; ordinals are contiguous; occurrence
time is nondecreasing; terminal states cannot transition; failure metadata is
bounded and code-consistent. `recorded_at` preserves the database system clock
separately. Updates and deletes are rejected.

## Security and privacy

The public schema stores no raw record, source-table name, source identifier,
image, credential, provider payload, raw exception, or organization-specific
fixture. Scope references existing corporate/process-unit identities or a
bounded thread key; it does not trust token claims as database truth. Future API
access reuses current RBAC/ABAC until a separate accepted RLS decision exists.

## Failure behavior

- malformed digests, unsupported enum codes, negative counts, missing request
  actors, same-actor duplicate idempotency keys, and incoherent scopes fail in
  PostgreSQL;
- evidence unavailable at a run cutoff fails before run creation;
- immutable snapshot/count/run/scope changes fail closed;
- status histories with illegal starts, gaps, reversed time, invalid
  transitions, or post-terminal appends fail closed;
- lookup-code category collisions abort migration;
- rollback refuses any non-empty registry relation.

## Deployment

The product PostgreSQL image applies migration 0018 after migration 0017. No new
service or container is introduced. A later API/outbox slice may use these
relations but cannot claim implementation from this schema alone.

## Testing

Static tests run without external services and lock file names, table names,
clock ownership, actor/idempotency scope, lookup inventory, Docker migration
order, temporary-artifact absence, and fail-closed rollback markers. Real
PostgreSQL tests use the committed migration files, generated quoted database
identifiers, preserved DSN query options, and actual database exceptions. They
exercise multiple run cutoffs over one snapshot, leakage rejection, immutable
and concurrency-frozen evidence, account-scoped idempotency, scope shape,
ordered lifecycle transitions, migration replay, and rollback. Hosted exact-head
CI remains authoritative for the PostgreSQL lane.

## Deferred work

API repository methods, Valkey outbox persistence, TEPP submission,
contextual-orchestrator task envelopes, React/Storybook surfaces, RLS, signed
acceptance manifests, artifact registries, and retention tooling are separate
reviewable slices.

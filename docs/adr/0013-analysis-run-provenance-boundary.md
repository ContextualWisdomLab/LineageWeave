# ADR 0013 — Normalized analysis-run provenance boundary

**Status:** Proposed  
**Date:** 2026-08-15  
**Decision owners:** LineageWeave product and data architecture  
**Depends on:** ADR 0001, ADR 0003, ADR 0004, ADR 0011; TEPP ADR 0011 and proposed ADR 0017

## Context

Milestone 2 executes LineageWeave against an operator-controlled PostgreSQL
source and combines product reconstruction with TEPP, contextual-orchestrator,
and fast-mlsirm. The product must prove which source snapshot, temporal cutoff,
configuration, service calls, and artifacts produced a result. At the same time,
the public repository and routine operational telemetry must never reveal the
private SQL, DSN, raw source rows, image bytes, provider credentials, or private
source identifiers.

A prior experimental implementation stored multiple service-specific run tables
with JSON-shaped metadata. Copying that schema into the protected product would
create duplicated status vocabularies, weak referential integrity, and an
unbounded channel for source content. It would also make the same analysis look
like unrelated TEPP, orchestrator, and report runs instead of one provenance
trace.

TEPP's accepted temporal baseline distinguishes evidence availability from the
analysis knowledge cutoff. Proposed TEPP ADR 0017 further assigns exact evidence
identity, model profiles, and downstream service boundaries to TEPP; LineageWeave
may align with that boundary but cannot claim its implementation until that ADR
and its production slice are accepted. A LineageWeave run therefore needs a
normalized source snapshot that rejects future-information leakage before any
derived product claim is accepted.

## Decision

LineageWeave adds seven third-normal-form tables:

- `analysis_source_profile` — immutable opaque query profile revision and exact
  query digest; never the query text or DSN;
- `analysis_source_snapshot` — aggregate counts, source digest,
  `maximum_available_time`, and `knowledge_cutoff`;
- `analysis_run_record` — one idempotent product run and lifecycle status;
- `analysis_run_configuration` — the bounded configuration that depends only on
  the run;
- `analysis_run_event` — append-only status evidence with actor, occurrence
  time, recording time, and payload digest;
- `analysis_service_run` — version-neutral child calls to TEPP,
  contextual-orchestrator, or fast-mlsirm;
- `analysis_artifact_record` — digest and external reference for aggregate,
  reproducibility, or browser evidence.

`analysis_source_snapshot` enforces:

```text
maximum_available_time <= knowledge_cutoff
```

This is the aggregate acceptance gate for TEPP's no-future-information
contract. Per-document clocks remain TEPP evidence authority; LineageWeave does
not collapse TEPP's event, assertion, document, system, available, and cutoff
clocks into one date.

All run, service, event, and artifact kinds live in `common_lookup_value`.
Database object names contain at least two `snake_case` words. The product
repository exposes only source-safe summaries: opaque profile key and revision,
digests, counts, clocks, configuration, and status. It never returns source SQL,
DSNs, raw rows, source table names, content, artifact bytes, credentials, or
private file paths.

The Python contract in `lineageweave.analysis_run` validates the same digest,
clock, count, and output rules before persistence. The repository in
`backend.app.analysis_run_ingestion` writes profile → snapshot → run →
configuration → event in one PostgreSQL transaction and fails closed when an
immutable key is reused with different evidence.

## Ownership and service boundaries

- LineageWeave owns product-run provenance and the buyer-facing read projection.
- TEPP owns exact evidence spans, multilingual semantic measurement, temporal
  validity, model-profile budgeting, and calibrated measurement artifacts.
- contextual-orchestrator owns provider routing and workflow traces, not source
  evidence or LineageWeave authorization.
- fast-mlsirm owns numerical psychometric artifacts, not product-run state.
- Private source SQL and credentials remain deployment secrets outside the
  product database and outside public source control.
- Aggregate actual-data acceptance manifests remain deployment artifacts; the
  public repository stores only their schema and digest contract.

## Alternatives considered

1. **Store source SQL and DSN in the run table.** Rejected because telemetry,
   support exports, or database access could disclose infrastructure and private
   source identity.
2. **One JSON metadata column per service.** Rejected because core fields lose
   foreign keys, temporal constraints, and stable query semantics.
3. **Separate TEPP, orchestrator, and report run roots.** Rejected because the
   product cannot reconstruct one end-to-end derivation or enforce a shared
   idempotency boundary.
4. **Store only logs.** Rejected because logs are not a normalized source of
   truth, are often sampled or deleted, and cannot enforce referential or
   temporal constraints.
5. **Normalized aggregate provenance with external artifact references.**
   Selected.

## Consequences

### Positive

- private-source analysis can be audited without publishing source identity;
- a historical run fails before persistence when evidence became available
  after its knowledge cutoff;
- retries are idempotent and evidence conflicts are explicit;
- TEPP, orchestrator, and fast-mlsirm calls share one parent lineage;
- operators can inspect run state through a stable, content-redacting API in a
  later UI slice;
- aggregate acceptance evidence can be retained outside source control and
  verified by digest.

### Costs

- operators must manage an external source-profile/query registry;
- actual data counts and digests must be computed before registration;
- service-specific diagnostic detail belongs in signed artifacts or service
  traces, not arbitrary run-table JSON;
- a subsequent migration and UI slice must attach existing experimental run
  evidence to this normalized model.

## Security and privacy

The design preserves authorized PII in the private source and product tables
where the business requires it; it does not blanket-mask operational data.
Instead, it minimizes broadcast and provenance surfaces. Audit output contains
only opaque IDs, hashes, aggregate counts, policy versions, clocks, and status.

An idempotency, profile, or snapshot collision with different evidence raises a
content-redacting conflict. Source content never appears in exception text. The
product API must apply authenticated administrator authorization before exposing
run summaries.

## Verification

Acceptance requires:

- production statement and branch coverage of the new Python modules at 100%;
- real PostgreSQL migration tests for normal insertion, temporal leakage
  rejection, unique profile revisions, digest validation, and foreign keys;
- deterministic request digests across JSON key order;
- no source SQL, DSN, table name, raw content, image bytes, or artifact bytes in
  public summaries;
- fresh-install Docker coverage of migration `0018`;
- exact-head product, security, SAST, and independent review gates;
- a private operator run that records only aggregate evidence and keeps its
  acceptance manifest outside public source control.

## Rollback

Rollback stops new run registration and removes `0018` tables only after all
external artifacts are retained and no downstream foreign key depends on them.
It never copies private source SQL into an older log-based path. Supersession
requires another ADR preserving normalized provenance, no-future-information
enforcement, source redaction, and service ownership boundaries.

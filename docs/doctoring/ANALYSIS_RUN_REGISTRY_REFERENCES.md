# Analysis-run registry standards and research traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** Migrations 0018–0019, ADR 0013 / 0017, rollback, and real-PostgreSQL contract tests.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C PROV-DM and PROV-O | Preserve identifiable entities, activities, agents, generation/use, and derivation without flattening provenance into display-only edges. | `analysis_source_snapshot`, `analysis_run`, authenticated requester, append-only status events, immutable digests; later product bindings continue to use the separate `provenance_*` layer from ADR 0011. |
| W3C Time Ontology in OWL | Keep temporal concepts explicit and avoid collapsing distinct clocks. | Evidence availability and snapshot capture remain on `analysis_source_snapshot`; analysis knowledge cutoff and request time remain on `analysis_run`; status occurrence and database record time remain distinct. `GET /api/analysis-runs/{id}` visible posts apply `created_at <= knowledge_cutoff` (ADR 0016). |
| ISO 8601-1:2019 | Use unambiguous timestamp representation and timezone-aware persistence. | PostgreSQL `timestamptz` for availability, capture, cutoff, request, occurrence, and record clocks; tests use explicit `Z` offsets. |
| PostgreSQL 18 constraints and trigger contracts | Put integrity close to durable truth and use constraints for row shape while triggers enforce cross-row state and serialization. | Digest/check constraints, category allowlists, account-scoped uniqueness, shape constraints, immutable-row triggers, shared snapshot-row locking, and serialized status transitions. |
| NIST SP 800-92 | Treat audit records as bounded, protected operational evidence rather than unstructured application logging. | Append-only status events, machine failure codes, actor identity, occurrence/record clocks, fail-closed rollback, and exclusion of raw source/provider payloads. |
| OpenAPI 3.2.0 | Define explicit versioned API schemas rather than exposing database rows or implementation-specific payloads. | API intentionally deferred; ADR 0013 requires a source-redacting run list/detail contract before a product surface is claimed. |

## Temporal reasoning

The registry applies a bitemporal discipline without claiming a complete
general-purpose bitemporal database:

- `maximum_available_time` answers when the newest admitted evidence became
  knowable;
- `captured_at` answers when the immutable source snapshot was materialized;
- `knowledge_cutoff` answers what a specific analysis was allowed to know;
- `requested_at` answers when that analysis was requested;
- `occurred_at` and `recorded_at` distinguish lifecycle occurrence from durable
  database recording.

The database requires the aggregate leakage boundary:

```text
maximum_available_time <= knowledge_cutoff <= requested_at
captured_at <= requested_at
```

TEPP remains the authority for finer event/assertion/document/system/available
clocks and temporal psychometrics. The registry does not duplicate TEPP
measurement outputs.

## Audit and privacy boundary

The registry may store:

- opaque product UUIDs;
- authenticated account UUIDs;
- SHA-256 digests;
- bounded configuration/version identifiers;
- aggregate counts;
- bounded status/failure codes;
- timezone-aware clocks.

The registry must not store:

- source SQL or source-table names;
- DSNs, credentials, or provider secrets;
- raw posts, HTML, images, base64 data, or attachments;
- model prompts/responses or raw exceptions;
- another service's application tables;
- organization-specific source identifiers in public fixtures or documentation.

Necessary PII remains available in its purpose-bound authorized product/source
context. Auditability is achieved with actor identity, access control,
provenance, retention, and immutable evidence rather than blanket masking.

## Verification matrix

| Claim | Falsifiable test |
|---|---|
| One snapshot supports multiple analyses | Insert two runs over one snapshot with different valid cutoffs. |
| Future evidence is excluded | Reject a run whose cutoff precedes the snapshot's maximum availability time. A late own-corp post stays out of `visible_posts`. |
| Evidence cannot change after derivation | Reject snapshot/count updates and count insert/delete after the first run. |
| Count/run race is serialized | Both paths acquire the snapshot row first; a later concurrency test must prove one legal winner and no lost freeze. |
| Request identity is stable | Reject analysis-run updates; scope and lifecycle live in their own relations. |
| Idempotency is actor-scoped | Permit identical opaque keys for two accounts and reject reuse by the same account. |
| Lifecycle is ordered | Require pending first, contiguous ordinals, monotonic time, legal transitions, terminal finality, and append-only rows. |
| Rollback does not erase audit data silently | Reject 0018 rollback with any registry rows. A run-bearing registry empties only through `purge_analysis_run_registry('approved-retention-purge')`; a wrong token and a raw `DELETE` stay rejected. Export then delete `analysis_run_retention_event` before 0019 rollback. |

## APA 7th references

International Organization for Standardization. (2016). *ISO 15489-1:2016:
Information and documentation—Records management—Part 1: Concepts and
principles*.

International Organization for Standardization. (2019). *ISO 8601-1:2019: Date
and time—Representations for information interchange—Part 1: Basic rules*
(confirmed 2024; Amendment 1:2022).

Kent, K., & Souppaya, M. (2006). *Guide to computer security log management*
(NIST Special Publication 800-92). National Institute of Standards and
Technology. https://doi.org/10.6028/NIST.SP.800-92

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

OpenAPI Initiative. (2025). *OpenAPI specification, version 3.2.0*.
https://spec.openapis.org/oas/v3.2.0.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
5.5. Constraints*. https://www.postgresql.org/docs/current/ddl-constraints.html

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C Recommendation).
https://www.w3.org/TR/owl-time/

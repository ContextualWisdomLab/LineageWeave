# ADR 0263: Authorized job-family and job-series snapshot import

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** ADR 0001, ADR 0065, ADR 0248, ADR 0252

## Context

The official SOC and O*NET classifications describe occupations; ADR 0252
therefore prohibits treating them as an employer's job family, job series, or
position. The product nevertheless needs to preserve an authorized
organization's own job architecture without deriving a crosswalk from codes or
labels and without committing its records.

W3C ORG separates a role taxonomy from a person, membership, organization, and
post, and recommends SKOS for taxonomic role structures. PROV-O separates an
entity's generation/invalidation history from domain validity. OPM's handbook
also distinguishes occupational groups, series, positions, and job-family
classification standards. These authorities support separate identities and
source assertions; none authorizes a universal employer crosswalk.

## Decision

1. Import only a caller-authorized, SHA-256-pinned source snapshot into four
   third-normal-form tables: source, node, hierarchy edge, and explicit
   occupation binding. Runtime records stay outside git; repository tests use
   synthetic rows only.
2. A node is exactly `job_family` or `job_series`. It is never an SOC/O*NET
   occupation, organizational unit, person, position, competency, or measured
   trait. The source code, label, description, and optional validity dates are
   preserved without normalization.
3. Hierarchy is an edge table, not a parent column. This preserves a
   source-declared series in multiple families and rejects missing endpoints,
   self-links, and cycles. No label, code shape, lexical similarity, embedding,
   or LLM may create an edge.
4. An occupation binding exists only when the source supplies the scheme IRI,
   scheme version, occupation code, and relation code together. A title that
   resembles an occupation code remains unbound.
5. Snapshots are immutable system-time evidence. A changed source requires a
   new snapshot code; divergent reuse of a snapshot/node/edge/binding identity
   fails through immutable-update triggers. Optional `valid_from`/`valid_to`
   record source validity and never invent missing dates.
6. The corporate entity must already exist. Imports neither create an
   organization nor infer authorization. Entity-first indexes bound the
   organization-scoped read path; physical partitioning is deferred until
   observed cardinality or lock evidence justifies a non-arbitrary boundary.
7. This contract publishes no person assignment, recommendation, competency
   score, importance weight, psychometric estimate, or causal claim. Those need
   their owning authorization and measurement decisions.

## Consequences

LineageWeave can represent employer-specific family/series structure without
polluting the public occupational vocabulary or leaking runtime data. Multiple
membership and temporal validity remain source evidence. API, UI, RDF
projection, and person/post binding remain unavailable until separate accepted
decisions define authorization and customer actions.

## Verification

- `tests/test_import_job_architecture.py` proves multiple membership, explicit
  binding, no label binding, cycle rejection, and incomplete-source rejection.
- `tests/test_job_architecture_schema.py` pins normalized identities,
  immutability, kind separation, and occupation-scheme separation.
- PostgreSQL integration must prove replay-safe migration, idempotent identical
  import, and divergent snapshot rejection before protected delivery.

## References

See
[`docs/doctoring/JOB_ARCHITECTURE_REFERENCES.md`](../doctoring/JOB_ARCHITECTURE_REFERENCES.md).

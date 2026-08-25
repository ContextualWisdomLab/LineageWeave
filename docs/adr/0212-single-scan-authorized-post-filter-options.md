# ADR 0212: Single-scan authorized post-filter options

- Status: Accepted
- Date: 2026-08-25

## Context

`GET /api/posts` must return every visibility and VOC-type option represented
in the caller's authorized, current source-post population, not merely values
on the requested page. The projection applied the same ABAC and source-post
eligibility predicate in two sequential `SELECT DISTINCT` queries. An
application-ready local stack with 43,189 aggregate `source_post` rows showed
repeated filter-option queries active in PostgreSQL while `/api/posts` exceeded
30 seconds. That stack used an older backend image, so this is diagnostic
evidence for the query shape, not PR-head latency evidence or a product SLO.

## Decision

Project both lookup dimensions from one ABAC-filtered `source_post` relation
using a lateral two-row value projection, then deduplicate by lookup category
and code. Join `common_lookup_value` by both category and code, and partition
the result into the existing response fields in application code.

The query keeps the complete authorized population and the existing public,
corporate-entity, process-unit, and source-eligibility predicates. It does not
derive options from the paginated result and does not cache options across
principals. No latency threshold is adopted; capacity remains an observed
property of a named environment and workload.

## Consequences

- Each post-list request performs one database round trip and one authorized
  source relation scan for both option dimensions instead of two sequential
  round trips and scans.
- Filter completeness and ABAC semantics remain unchanged.
- A focused unit test guards the one-query contract and bound ABAC parameters;
  the existing authenticated integration test continues to guard visible
  posts and complete option values.
- Runtime comparison still requires an exact-head application image and the
  synthetic k6 procedure; older-image observations cannot establish the
  improvement's latency effect.

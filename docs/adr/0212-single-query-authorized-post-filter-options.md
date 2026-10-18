# ADR 0212: Single-query authorized post-filter options

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

- Each post-list request performs one database query and round trip for both
  option dimensions instead of two sequential queries and round trips. The
  physical scan plan is not asserted until an exact-head `EXPLAIN` is recorded.
- Filter completeness and ABAC semantics remain unchanged.
- A focused unit test guards the one-query contract and bound ABAC parameters;
  the existing authenticated integration test continues to guard visible
  posts and complete option values.
- Runtime comparison still requires an exact-head application image and the
  synthetic k6 procedure; older-image observations cannot establish the
  improvement's latency effect.

## Amendment candidate — 2026-10-19: reuse the authorized source set

### Context

An authenticated k6 observation on the canonical local Compose stack found
PostgreSQL near four busy CPU cores as read latency rose with concurrency.
An isolated post-list read took about 936 ms, while the filter-option query
alone took 226–238 ms in three direct observations. The original lateral
projection still satisfies the one-query contract, but its scan and deduplication
work is material at the observed 43,189-row local size. These are diagnostic
measurements, not a production capacity threshold.

### Decision

Materialize the same ABAC- and eligibility-filtered Post identity, visibility,
and primary Voice once within the existing database query. Union the visibility
codes with current Voice codes, retaining the primary code when no current
association exists. Keep the category-qualified lookup join, deterministic
ordering, bound scope parameters, and one database round trip. This replaces
the lateral two-row projection; it does not change the API or Voice policy.

### Consequences and alternatives

The candidate returned the same option codes and labels in the local comparison
and took 92–144 ms in three observations. The materialized relation uses memory
proportional to the authorized Post count and may spill at a larger deployment;
its exact-head application latency remains unverified. Keeping the lateral
projection preserves behavior but retains the measured cost. Per-code existence
queries were rejected for this slice because they would repeat the scoped Post
predicate without comparative evidence.

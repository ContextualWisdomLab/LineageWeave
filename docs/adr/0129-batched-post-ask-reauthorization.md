# ADR 0129: Batch persisted post-Ask reauthorization

- Status: Proposed on issue #358; not protected-main behavior
- Date: 2026-08-22
- Figma file: N/A (backend-only read-path change; no visual behavior changes)
- Depends on: ADR 0113 and ADR 0128

## Context

The post Ask-history endpoint loads every persisted exchange and then reauthorizes
each citation set separately. The authorization result is correct and fail-closed,
but the endpoint uses one history query plus two serialization queries and one
authorization query per exchange. Database round trips therefore grow as
`1 + 3N`, making a long but valid history visibly slower.

Batching must not turn prior authorization into implicit trust. NIST SP 800-207
requires access decisions to remain resource-oriented rather than relying on
network location or an earlier session (Rose et al., 2020). Each exchange must
therefore retain its own persisted knowledge cutoff, tenant ABAC evaluation, and
publication-eligibility check.

## Decision

1. Load at most 64 persisted exchanges and 256 citation occurrences in one
   bounded history query. A 65th exchange or 257th citation produces a typed,
   fail-closed error; neither collection is silently truncated.
2. Reauthorize all loaded citation sets in one repository query. Flatten equal-
   length arrays of exchange ordinal, citation ordinal, citation UUID, and cutoff,
   validate every value before SQL, and use PostgreSQL's multi-array `unnest` in
   the `FROM` clause. PostgreSQL pads unequal arrays with `NULL`, so application
   validation and construction must keep their lengths equal (PostgreSQL Global
   Development Group, 2026).
3. Apply source publication eligibility, tenant ABAC, and the row's own knowledge
   cutoff inside the batched query. Partition results by exchange ordinal and
   reuse the existing citation/project projection logic.
4. Preserve persisted exchange and citation ordering. If one exchange loses any
   citation, withhold only that exchange, including its answer prose, title,
   count, and project links.
5. Return an actionable service-unavailable response when persisted history
   exceeds the supported safety budget. No new purge or public retention route is
   introduced.

## Consequences

- After the existing parent-post visibility lookup, the history/reauthorization
  phase performs two data queries for any supported history size instead of
  `1 + 3N`.
- Mixed cutoffs remain independent within the same SQL statement.
- A bounded request can repeat a citation across exchanges because the persisted
  cutoffs may differ; the 256-occurrence budget accounts for each occurrence.
- Histories beyond the explicit budget remain stored but are not partially
  disclosed. An administrator must reduce retained history before retrying.
- No schema, UI, Project-history API, TEPP adapter, or model boundary changes.

## Verification

- Unit contracts compare 1, 10, and 64 exchanges with the existing per-exchange
  projection, cover invalid UUIDs and both limits before SQL, and prove one hidden
  citation removes only its exchange.
- Endpoint contracts count exactly two data queries independently of exchange
  count.
- A PostgreSQL integration contract executes mixed-cutoff and tenant-isolation
  cases against the actual query when the project integration DSN is available.
- Query-count and measured latency evidence belongs in
  `docs/product-technical-gap-baseline.md`.

## References

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
9.19. Array functions and operators*.
https://www.postgresql.org/docs/18/functions-array.html

Rose, S., Borchert, O., Mitchell, S., & Connelly, S. (2020). *Zero trust
architecture* (NIST Special Publication 800-207). National Institute of
Standards and Technology. https://doi.org/10.6028/NIST.SP.800-207

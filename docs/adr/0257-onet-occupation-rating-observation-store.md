# ADR 0257: O*NET occupation-rating observation store

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** ADR 0166, ADR 0255, ADR 0256

## Context

O*NET 31.0 publishes occupation-specific ratings for content-model abilities, essential and
transferable skills, knowledge, education, training and experience, interests,
work styles, work activities, work context, and adjacent content-model
domains. A rating is not merely an edge: its meaning depends on the release,
source table, occupation, element, scale, optional response category, sample
size, standard error, 95% confidence interval, precision-suppression flag,
relevance flag, source update month, and domain source. O*NET publishes that
field as a seven-character `MM/YYYY` value; coercing it to a database date
would invent a day (National Center for O*NET Development, 2026b).

Flattening those attributes into ontology predicates would erase measurement
and provenance boundaries. Loading them into Python mathematical code would
also violate LineageWeave's externalized-compute boundary.

## Decision

1. Store source releases, source tables, scales, occupations, content-model
   elements, and rating observations in separate third-normal-form tables.
2. Preserve published numeric values exactly as decimal observations. They are
   source ratings, never locally estimated weights, person scores, causal
   effects, or calibrated psychometric parameters.
3. An observation key is release + source table + occupation + element + scale
   + optional category. PostgreSQL `UNIQUE NULLS NOT DISTINCT` keeps an absent
   category an honest single absence rather than replacing it with a sentinel.
4. Partition observations first by release and then by source-table code.
   These are authoritative lifecycle/query boundaries and require no invented
   hash modulus. An importer must create both exact LIST partitions before
   inserting; without them PostgreSQL rejects the row.
5. Every insert uses the owning release/table artifact digest and idempotent
   `ON CONFLICT DO NOTHING`. An exact duplicate is idempotent, while a row with
   the same identity and different source values fails closed. Endpoint names
   and scale names must match their normalized reference
   rows; each scale definition names its owning source-table artifact, and the
   importer rejects disagreement rather than overwriting identity.
6. Preserve `recommend_suppress` and `not_relevant` independently. A suppressed
   value remains stored with its warning; a not-relevant value is not converted
   to zero. Missing `n`, error, or interval values remain null.
7. Range and uncertainty constraints reject negative sample/error values,
   inverted confidence intervals, malformed or future source update months, malformed source
   digests, and values outside their declared scale bounds before persistence. Scale bounds
   govern the published `Data Value`, not the optional response-category code. In particular,
   O*NET's `CXP` rows store a category in `Category` while `Data Value` is the percentage that
   endorsed it, so the authoritative `CXP` bounds are 0 through 100 (National Center for
   O*NET Development, 2026b).
8. This content-model-element store excludes Task Ratings, whose integer Task
   IDs and task-statement identity require a separate normalized target table;
   it does not reinterpret a Task ID as a content-model element.
9. This store is immutable source evidence. Row mutation and whole-store
   truncation fail closed. Any later aggregation, comparison,
   temporal model, multilevel model, or occupational recommendation belongs to
   TEPP/fast-mlsirm or another owning Rust service and must cite these rows.
10. `scripts/import_onet_ratings.py` accepts one caller-pinned official CSV and
   Scales Reference file. It verifies both artifact SHA-256 values and row
   counts, exact scale names and bounds, reference-name consistency, finite
   decimals, Y/N/blank flags, optional Category and Not Relevant columns,
   exact `MM/YYYY` source months, and observation-key uniqueness before opening the
   target connection. A transaction-scoped advisory lock serializes one
   release's partition DDL.

## Consequences

LineageWeave can import the governed public O*NET content-model rating corpus without
manufacturing semantics or embedding large production datasets in git.
Release/source partitions localize hot imports and permit exact detach/archive
operations. The same pinned artifact is idempotent; a reused release, source,
scale, occupation, or element identity with different source metadata fails
closed. A separate API/UI ADR is still required before exposing ratings.

## References

National Center for O*NET Development. (2026a). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

National Center for O*NET Development. (2026b). *Work context: O*NET 31.0 data
dictionary*. https://www.onetcenter.org/dictionary/31.0/excel/work_context.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Table partitioning*. https://www.postgresql.org/docs/current/ddl-partitioning.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
CREATE TABLE*. https://www.postgresql.org/docs/current/sql-createtable.html

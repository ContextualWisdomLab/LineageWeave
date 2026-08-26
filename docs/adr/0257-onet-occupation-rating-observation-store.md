# ADR 0257: O*NET occupation-rating observation store

**Status:** Accepted  
**Date:** 2026-08-27  
**Extends:** ADR 0166, ADR 0255, ADR 0256

## Context

O*NET 31.0 publishes occupation-specific ratings for abilities, essential and
transferable skills, knowledge, education, training and experience, interests,
work styles, work activities, work context, and adjacent content-model
domains. A rating is not merely an edge: its meaning depends on the release,
source table, occupation, element, scale, optional response category, sample
size, standard error, 95% confidence interval, precision-suppression flag,
relevance flag, update date, and domain source.

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
   `ON CONFLICT DO NOTHING`. Endpoint names and scale names must match their normalized reference
   rows; each scale definition names its owning source-table artifact, and the
   importer rejects disagreement rather than overwriting identity.
6. Preserve `recommend_suppress` and `not_relevant` independently. A suppressed
   value remains stored with its warning; a not-relevant value is not converted
   to zero. Missing `n`, error, or interval values remain null.
7. Range and uncertainty constraints reject negative sample/error values,
   inverted confidence intervals, future source update dates, malformed source
   digests, and values outside their declared scale bounds before persistence.
8. This store is immutable source evidence. Any later aggregation, comparison,
   temporal model, multilevel model, or occupational recommendation belongs to
   TEPP/fast-mlsirm or another owning Rust service and must cite these rows.

## Consequences

LineageWeave can import the complete public O*NET rating corpus without
manufacturing semantics or embedding large production datasets in git.
Release/source partitions localize hot imports and permit exact detach/archive
operations. A separate API/UI ADR is still required before exposing ratings.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Table partitioning*. https://www.postgresql.org/docs/current/ddl-partitioning.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
CREATE TABLE*. https://www.postgresql.org/docs/current/sql-createtable.html

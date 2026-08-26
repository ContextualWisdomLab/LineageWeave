# ADR 0258: Authenticated occupation-rating source read API

**Status:** Accepted

**Date:** 2026-08-27
**Extends:** ADR 0120, ADR 0184, ADR 0257

## Context

ADR 0257 preserves released occupation-to-element observations, but a database
import alone does not let a product user inspect what a job profile says. A
read contract must distinguish an unimported source from an imported source
with no row for one occupation, preserve low-precision and not-relevant flags,
and avoid presenting a published rating as a local weight or recommendation.

## Decision

1. Add an authenticated, read-only occupation-rating endpoint. O*NET source
   observations are licensed public reference data and are not tenant records;
   any authenticated LineageWeave account may read an imported artifact.
2. Require exact release, source-table, and O*NET-SOC codes. Return
   `source_available=false` when that pinned artifact is not imported; return
   `source_available=true` with an empty item list when it is imported but has
   no observation for the requested occupation.
3. Return the rating and Scales Reference artifact URLs, SHA-256 values, and
   row counts. Every observation retains element/scale identity, declared
   bounds, optional category, exact decimal strings, sample/error/interval,
   suppression, relevance, source month, and domain source.
4. Order by element, scale, and category and use bounded offset pagination.
   Per-occupation source partitions bound this projection; a cursor needs a
   later decision only if measured production latency requires it.
5. Do not aggregate, rank, normalize, infer person traits, or recommend an
   occupation. Suppressed values remain visible with the suppression flag so a
   user can audit the source without mistaking low precision for absence.
6. API and frontend copy describe the evidence and the user's next action,
   never importer, partition, model-provider, or orchestration internals.

## Consequences

The semantic layer gains an honest product read boundary without duplicating
psychometric arithmetic. An accessible UI and its Storybook states remain a
separate delivery step after this API has authenticated runtime evidence.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Queries—limit and offset*. https://www.postgresql.org/docs/current/queries-limit.html

# ADR 0256: O*NET content-model published linkages

**Status:** Accepted  
**Date:** 2026-08-27  
**Extends:** ADR 0248, ADR 0255

## Context

O*NET 31.0 publishes eight explicit linkage tables connecting Abilities,
Essential Skills, Transferable Skills, and Work Styles to relevant Work
Activities and Work Context elements. These 1,417 source pairs provide an
authoritative relationship layer without deriving relations from labels,
embeddings, local judgment, or arbitrary weights.

## Decision

1. Publish all eight tables and all 1,417 unique directed pairs. Preserve the
   source and target O*NET element IDs and names exactly and fail generation
   when either endpoint is absent from the pinned Content Model Reference.
2. Assert `:relevantWorkActivity` or `:relevantWorkContext` from the worker
   element to the job element. Direction is preserved; the predicates are not
   symmetric, causal, equivalent, or psychometric weights.
3. Reify every direct assertion as an `rdf:Statement` and `prov:Entity` with
   exact `rdf:subject`, `rdf:predicate`, `rdf:object`, and
   `prov:wasDerivedFrom` pointing to the one pinned O*NET table that published
   it. No unsupported confidence or generated time is added.
4. Pin each official O*NET 31.0 JSON artifact and reproduce one deterministic
   Turtle fragment. A duplicate pair inside a source table, endpoint-name
   mismatch, unknown endpoint, wrong domain, or wrong row count fails closed.
5. Keep occupation-specific ratings separate. This decision imports no
   occupation code, data value, scale, sample size, error, confidence interval,
   suppression flag, person trait, or locally normalized score.

## Consequences

The semantic layer can traverse published cognition/style-to-behavior/context
relations with assertion-level provenance. Occupation ratings remain the next
separate import contract because their scales, uncertainty, suppression, and
update dates cannot be represented as these unweighted vocabulary links.

## Reference

National Center for O*NET Development. (2026). *O*NET 31.0 database: Content
model linkages* [Data set]. https://www.onetcenter.org/dictionary/31.0/json/

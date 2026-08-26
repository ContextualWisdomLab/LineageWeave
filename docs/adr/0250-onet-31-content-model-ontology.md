# ADR 0250: O*NET 31.0 content-model semantic layer

**Status:** Accepted  
**Date:** 2026-08-27  
**Extends:** ADR 0245, ADR 0248, ADR 0249

## Context

The high-level concepts in ADR 0245 cannot address most work-related
cognition, affect, behavior, requirements, activities, or context. O*NET 31.0
publishes 3,006 content-model elements with stable element IDs, names,
descriptions, and a documented outline hierarchy encoded in those IDs.

## Decision

1. Publish all 3,006 Content Model Reference rows as SKOS concepts in a
   versioned `:onet31ContentModelScheme`.
2. Preserve `element_id`, name, and description verbatim. Derive
   `skos:broader` only by O*NET's documented rule: remove the final
   period-delimited outline segment. A missing parent fails generation.
3. Type each node by the six published root domains and, where present, the 18
   published second-level branches. These types are navigation boundaries, not
   psychometric scales or assertions about a person.
4. Keep Work Styles distinct from affective reactions and abilities distinct
   from observed performance. Do not infer occupation ratings, person traits,
   causal relations, weights, or crosswalks from this vocabulary.
5. Pin the exact O*NET 31.0 JSON artifact SHA-256
   `db59c30e4240931edce59310f2747f5476f058984b55f58f72c6f29faa30186f`
   and verify deterministic Turtle reproduction.

## Consequences

The semantic layer can address the complete published O*NET conceptual
vocabulary. Occupation-specific observations and the separately published
ability/skill/style-to-activity/context linkages remain provenance-bearing
data imports governed by later decisions.

## Reference

National Center for O*NET Development. (2026). *O*NET 31.0 database: Content
Model Reference*. https://www.onetcenter.org/dictionary/31.0/json/content_model_reference.html

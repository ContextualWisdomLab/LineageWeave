# ADR 0160 — Corroborated SKOS aliases bind one corporate catalog row

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

[ADR 0008](0008-organization-abbreviation-resolution.md) persists a
search-corroborated `skos:altLabel` / `skos:prefLabel` pair (Miles &
Bechhofer, 2009) in `organization_name_resolution`. Keyman then
substitutes the canonical name before
`get_or_create_corporate_entity`. That rewrite is not enough.

`score_corporate_entity` only compares the mention to
`corporate_entity.entity_name`. An initialism such as the synthetic
fixture `AGP` shares almost no substring with `Aurora Grid Power`
(Bhattacharya & Getoor, 2007 candidate generation). If a catalog row
was created under the short form before corroboration, a later
canonical mention misses and ADR 0010 may insert a second `AUTO-`
row. The reverse is also true: a catalog row stored under the
preferred label does not bind a later abbreviated mention when
resolution is unavailable on that request.

The product gap baseline described this as missing abbreviation
mapping. Repository artifacts may only use synthetic names
([ADR 0001](0001-demo-identity-and-data-boundary.md)).

## Decision

After loading `corporate_entity` candidates, expand them with every
`verify_corroborated` SKOS pair:

- a row whose `entity_name` matches the preferred label also competes
  under the alternative label;
- a row whose `entity_name` matches the alternative label also
  competes under the preferred label.

The expansion is a virtual candidate with the **same**
`corporate_entity_id`. Score the raw catalog first. Alias labels enrich
candidates only after a raw miss; they never override a raw unique result
or tie (ADR 0026). An alias label binds only on exact normalized equality;
short near-matches do not inherit the raw catalog's fuzzy threshold.
Uncorroborated or pending pairs are not loaded.
Identical or empty labels are ignored.

Under the creation lock, reload both the catalog and corroborated aliases.
First repeat ADR 0026's normal-threshold raw classification, excluding only
the ancestor path resolved by the current recursion; then run the alias-expanded
exact check (`min_similarity=1.0`). A concurrent catalog row stored under the
other label is therefore reused instead of inserting a duplicate.

Synthetic fixtures only: `AGP` / `Aurora Grid Power` (and similarly
`NRG` / `Northridge Grid` where already present). Real organization
names must not appear in tests, seeds, or docs.

## Consequences

- Two corroborated names for the same organization bind one catalog
  row in Keyman affiliation and R&R organization-role resolution.
- Live customer abbreviations still require the ADR 0008
  resolve-then-verify pipeline at runtime; this decision does not
  ship a real-world alias table.
- Character-similarity matching remains candidate generation, not
  proof of identity.

## Related

Extends [ADR 0008](0008-organization-abbreviation-resolution.md) and
respects [ADR 0026](0026-tied-organization-similarity.md) and
[ADR 0010](0010-corporate-hierarchy-auto-creation.md).

## References (APA 7th)

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data, 1*(1), Article 5. https://doi.org/10.1145/1217299.1217304

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

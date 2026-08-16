# ADR 0010 — a real counterparty organization is auto-created into the corporate hierarchy, not left permanently unresolved

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

`lineageweave.corporate_hierarchy_resolution`'s similarity-based
matching only ever locates an *already-cataloged* `corporate_entity`
row -- it has no path to create one. This was fine while the only
`corporate_entity` catalog was synthetic demo fixtures with a handful
of names extraction would naturally already know. A synthetic batch
where the catalog holds only the employer's own two-row hierarchy
exposes the same gap: every counterparty named in a post is, by
definition, outside that catalog. Similarity matching then resolves
**0 affiliation rows and 0 R&R organization-actor mentions** -- the
standing integrated customer-affiliate tree requirement (Harbor Group
-> Harbor Devices Korea -> ... in the synthetic brief) stays empty
until a verified creation path exists.

## Decision

`get_or_create_corporate_entity` (`backend/app/corporate_entity_ingestion.py`)
extends the existing resolution pipeline with a creation fallback, not
a competing algorithm:

1. Try `resolve_corporate_entity` (similarity matching,
   Bhattacharya & Getoor, 2007; tied top scores stay unbound, ADR
   0021) first -- an already-cataloged entity still resolves exactly
   as before when the top score is unique.
2. On a miss, ask an LLM
   (`lineageweave.corporate_hierarchy_inference.CorporateHierarchyInferenceClient`)
   to propose this organization's place in the Group -> Company ->
   Plant hierarchy (`corporate_entity_level`, ADR 0004's existing SKOS
   `skos:broader`/`skos:narrower` structure) from the post's own text --
   never inventing a hierarchy the text gives no evidence for; the
   model may decline with `UNKNOWN`.
3. The proposal is only trusted after
   `lineageweave.relation_verification`'s existing Searxng
   corroboration (the same reused verification client
   `organization_name_resolution`/ADR 0008 already established this
   pattern for) -- an uncorroborated or unavailable-channel proposal
   creates nothing, same never-trust-an-unverified-guess discipline as
   every other channel here.
4. Only then is a real new `corporate_entity` row inserted. A proposed
   parent organization is itself resolved-or-created first (bounded to
   4 levels of recursion, so a misbehaving response chain cannot spin
   into unbounded row creation), so the whole chain gets real
   `parent_entity_id` links, not an orphaned single-level row.

**Auto-created code namespace**: `corporate_entity_code` is also the
real login "corp code" attribute Keycloak issues via the `corp_code`
token claim (`docker/keycloak/realm-export.json`) -- an auto-created
counterparty row must never collide with that namespace. Every
auto-created code is prefixed `AUTO-` followed by a deterministic hash
of the entity name (same name -> same code, so a genuine concurrent
duplicate-creation race collides on the real SQL `unique` constraint
and self-resolves via `on conflict`, rather than creating two rows for
one organization under two different codes).

Wired into both existing organization-resolution call sites --
`keyman_ingestion.py`'s person-affiliation loop and
`post_summary_ingestion.py`'s R&R organization-actor loop -- rather
than a third, separate code path, so both routes to `corporate_entity`
share one creation policy.

## Consequences

- A wrong hierarchy placement (level or parent) is a real risk this
  design accepts, bounded by the same LLM-judgment-call discipline
  ADR 0007's team-vs-organization classification already accepts: the
  raw name is never lost regardless (it is the `entity_name` itself),
  so a wrong placement is a correctable graph-structure error, not lost
  data.
- The `AUTO-` code namespace is a real, deliberate simplification: an
  operator wanting a genuinely curated corp-code scheme for these
  entities later would need to re-code them, not just re-run
  extraction -- accepted because the alternative (leaving every
  counterparty unresolved forever) is strictly worse for this
  product's actual purpose.
- Every LLM/search call in this path already existed for a different
  purpose (`organization_name_resolution`'s resolution call shape,
  `relation_verification`'s verification client) -- no new provider
  integration was built, keeping this consistent with the project's
  standing discipline of reusing an existing channel over adding a new
  one wherever the shape already fits.

## Related

Extends [ADR 0008](0008-organization-abbreviation-resolution.md)'s
reuse-the-verification-client pattern and
[ADR 0009](0009-cross-post-actor-identity.md)'s cross-post identity
work -- an R&R organization actor's identity is now genuinely resolved
to a real corporate hierarchy node, not left as free text even when no
prior mention of it existed anywhere in the dataset. A tied similarity
score stays unbound ([ADR 0021](0021-tied-organization-similarity.md)).

## References (APA 7th)

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, 1(1), Article 5. https://doi.org/10.1145/1217299.1217304

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal of the American Statistical Association, 64*(328), 1183–1210. https://doi.org/10.2307/2286061

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

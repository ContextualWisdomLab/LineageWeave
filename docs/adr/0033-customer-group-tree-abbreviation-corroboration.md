# ADR 0033 — Operators navigate a customer-group tree; abbreviations are Searxng-checked against that tree

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-17
**Depends on:** ADR 0004 SKOS Group / Company / Plant; ADR 0005 / 0008 Searxng verification; ADR 0010 hierarchy auto-creation (not redone here)

## Context

Live #74 already resolves abbreviated names (ADR 0008), infers a
Group / Company / Plant placement (ADR 0010), and renders a
**post-scoped** affiliate tree of Keymen on one record. Operators still
meet a flat corp list on home (`GET /api/me`) and have no catalog-wide
navigator. Abbreviations are paired to an LLM-proposed name, not
cross-checked against the tree the buyer can see.

A missing Searxng channel must not invent a parent or auto-create a
catalog row from a guess (Thorne, Vlachos, Christodoulopoulos, & Mittal,
2018; Fellegi & Sunter, 1969). Public git stays synthetic Demo Corp
only (ADR 0001).

## Decision

1. **Customer-group tree.** `GET /api/customer-group-tree` returns the
   authorized forest: affiliated `corporate_entity` rows plus ancestors
   and descendants, using the existing `corporate_entity_level` codes
   (`group`, `company`, `plant`). A catalog row the account does not
   touch is omitted. The React home panel is a nested list; a click
   opens that entity as the `corporate_entity` report grouping. This is
   not the post affiliate tree and does not embed raw HTML.
2. **Abbreviation cross-check against that tree.**
   `lineageweave.abbreviation_tree_corroboration` reuses
   `SearxngRelationVerificationClient`. It does not call an LLM and
   does not insert a `corporate_entity` row. A raw mention is queried
   against each authorized tree node. Exactly one corroborated node
   binds. Zero hits or a tie stay unbound. An unavailable or failed
   search is not recorded as uncorroborated: the write route returns
   503 when `SEARXNG_BASE_URL` is unset, and a raised search error
   propagates. Persistence is
   `abbreviation_tree_corroboration` (3NF; keyed by
   `raw_organization_name`).
3. **Seed.** Demo Group → Demo Corp → Demo Plant, plus a synthetic
   `DC` → Demo Corp corroborated fixture at
   `https://example.test/demo-corp-dc`.

ADR 0008 and ADR 0010 stay the LLM-expansion and AUTO-creation paths.
This slice does not replace them.

## Consequences

- Operators can walk the customer-group hierarchy without opening a
  post.
- An abbreviation that Searxng cannot uniquely place on the tree stays
  text. No parent is invented. No AUTO row is created from this path.
- Existing volumes apply `0027_abbreviation_tree_corroboration.sql`.
  Fresh `0001_initial_schema.sql` already contains the table.

## References — APA 7th

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data,
1*(1), Article 5. https://doi.org/10.1145/1217299.1217304

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage.
*Journal of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018).
FEVER: A large-scale dataset for fact extraction and VERification. In
*Proceedings of the 2018 Conference of the North American Chapter of
the Association for Computational Linguistics: Human Language
Technologies* (pp. 809–819). Association for Computational Linguistics.
https://doi.org/10.18653/v1/N18-1074

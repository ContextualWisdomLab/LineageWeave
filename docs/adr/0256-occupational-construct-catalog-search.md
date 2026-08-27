# ADR 0256: Authorized occupational construct catalog search

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0184](0184-ontology-provenance-explorer.md), [ADR 0248](0248-occupational-construct-evidence-boundary.md), [ADR 0250](0250-official-occupational-construct-catalog-sync.md), [ADR 0255](0255-occupational-construct-ontology-navigation.md)

## Context

ADR 0255 projects assertion-backed occupational constructs into the bounded
ontology neighborhood. Reviewers can walk from a visible Post to a versioned
O*NET concept, but they cannot start from a catalog label. A raw catalog
lookup would become a vocabulary oracle: it would disclose official membership
and descriptions even when the reviewer has no supporting Post.

PRD-FR-2B therefore left catalog search unavailable until this increment.

## Decision

1. `GET /api/occupational-constructs/search` matches the official preferred
   label or description of a synchronized O*NET 31.0 construct. The query is
   a case-insensitive exact-substring filter. LIKE metacharacters in the
   query are escaped so `%` and `_` stay literal. Fuzzy ranking, scores, and
   person/job inference stay unavailable.
2. A hit is admitted only when at least one source-eligible Post that passes
   the existing ABAC callback supports that construct. Hidden Posts never
   create a hit, fill a cursor, or change visible labels. Constructs with no
   visible support are omitted; missing and unauthorized catalog rows share
   the same empty page.
3. Conflicting truth statuses on the visible supporting Posts omit that
   construct, matching ADR 0255. `truth_rejected` and `truth_superseded` do
   not create a search hit.
4. Each hit names one supporting Post: the earliest visible availability
   instant (`greatest(post.created_at, assertion.generated_at)`), then Post
   id. The payload carries construct id/IRI/family/label, catalog version,
   that Post id and title, the verbatim evidence span, and the agreed truth
   status. It does not dump the official description, hidden totals, unit
   ids, or extraction method.
5. Continuation is a keyset on `construct_iri`. `OFFSET` is forbidden. The
   opaque cursor is the last returned official IRI; a tampered or non-O*NET
   cursor fails closed. Default page size is 20; the hard maximum is 50.
6. Optional `family` admits only `cognitive_ability`, `work_style`, and
   `work_activity`. Affective and performance families remain unavailable
   until an authoritative vocabulary is accepted. Optional `knowledge_cutoff`
   uses the same availability clock as ADR 0255.
7. The explorer hosts the search. It is not a new GNB destination. Customer
   copy tells the reviewer to type a catalog label and open the supporting
   record. Clicking a hit opens that Post.

## Consequences

- Reviewers can find Oral Comprehension (or another official label) across
  records they may already read, then open the cited Post.
- Catalog membership without visible evidence stays undisclosed.
- Occupation ratings, DPT crosswalks, and person traits remain out of scope.

## Verification

- Search tests cover substring escaping, family and cursor validation, hidden
  Post omission, truth-conflict omission, cutoff, pagination, and payload
  shape.
- Schema tests require replay-safe label/description indexes.
- Frontend tests cover short-query guidance, no-match and error states,
  click-to-open, family filter, and localized next actions. Storybook adds
  populated, empty, no-match, and loading scenes.

## References

See
[`docs/doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md`](../doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md).

Open Worldwide Application Security Project. (2023). *API1:2023 broken object
level authorization*. https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/

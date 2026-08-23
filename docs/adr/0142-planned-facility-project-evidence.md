# ADR 0142 — A planned facility becomes project/entity evidence only through the existing semantic-relationship channel, with an explicit "planned" predicate

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

`docs/product-technical-gap-baseline.md` (§5, item 3) records a live finding:
a key event whose text names a specific planned facility (its own example:
"X 충전소 구축 계획", i.e. "plan to build X charging station") produces
`key_events` / `key_event_details` prose only. It is never checked against
`post_project_mention` / the entity graph, so the facility itself is not
recognized as an entity, and no relationship is inferred between it and the
organization that the post's own R&R evidence says would operate it.

The gap doc is explicit that this needs its own ADR before any inference
code, because the risky part is not rendering — it is deciding *when* text
that describes a *plan* is allowed to become a persisted *relationship*.
ADR 0010's fail-closed hierarchy-creation design exists precisely to stop an
organization mention from being auto-created without independent
corroboration; inferring an "operates" relationship from event-adjacent
context risks the same class of mistake — asserting a fact ("Org X operates
Facility Y") that the source text does not actually state ("Org X plans to
build Facility Y").

The initial proposed revision was decision-only. The separately reviewed
follow-up now implements the accepted admission rule without adding a second
relationship table or catalog-creation path.

### What already exists that this can reuse

- `post_summary_semantic_relationship` / `SemanticRelationship`
  (`lineageweave/post_summary.py`) is already a generic, closed-vocabulary,
  evidence-required subject–predicate–object channel:
  `SEMANTIC_RELATION_NODE_TYPES` already includes `organization`,
  `industrial_asset`, `industrial_process`, `place`, and `project`;
  `SEMANTIC_RELATION_PREDICATES` is a closed set of PROV-O / SKOS / SOSA /
  ODRL / `lw_*` codes. A relationship row without a non-empty `evidence_text`
  is rejected by `SemanticRelationship.__post_init__` today.
- `post_project_mention` already records a project name/key with its own
  `mention_confidence` and `extraction_method`, independent of key events.
- Neither channel today has a predicate that means "named as the operator of
  a facility this post says is only planned, not existing."

Given this, the missing piece is not a new table or a new relationship
class — it is one new closed predicate code plus the admission rule that
governs when the extractor may emit it.

## Decision

1. **Reuse `post_summary_semantic_relationship`; do not add a new table.**
   Add one new predicate code, `lw_plans_to_operate`, to
   `SEMANTIC_RELATION_PREDICATES` and to `docs/ontology/lineageweave-kg.ttl`
   (`LW.predicateCode` / `LW.predicateIri` per `semantic_predicate_annotations`'s
   existing lookup contract). The subject is the organization/team actor
   named in the post's own R&R evidence as the one carrying out the plan;
   the object is the facility, typed `industrial_asset` (or `place` when the
   text gives no asset-specific detail).
2. **The predicate name itself carries the epistemic status.**
   `lw_plans_to_operate` names an announced intention, not a standing fact.
   The extractor must never emit `lw_has_actor`/`org_*` operate-style
   predicates for a facility the post itself describes only as planned or
   under construction. If a later post's evidence says the facility is
   actually operating, that is new evidence for a new relationship row (an
   `lw_supports`/successor predicate is a separate, future decision if that
   need materializes) — this ADR does not retroactively upgrade a prior
   "planned" row.
3. **Admission rule — every one of these must hold before the relationship
   is emitted:**
   - The post's own text (not the operator's inference, not world knowledge)
     names both the organization/team actor and the facility in the same
     event or adjacent evidence span.
   - The facility is also captured as a `post_project_mention` row (or is
     eligible to be, at extraction time) so the entity has independent
     project-evidence backing, not just a phrase inside `key_event_details`.
     A facility named only in event prose, with no corresponding project
     mention, does not qualify — this mirrors ADR 0010's requirement that
     enrichment corroborate before binding, not merely mention.
   - `confidence` reflects the extractor's own stated confidence in the
     *plan-to-operate* framing specifically, not the general event
     confidence. A low-confidence event does not get rounded up.
   - `evidence_text` is the literal source span naming both the actor and
     the facility (already required by `SemanticRelationship`, restated here
     because it is the actual safety mechanism: a reviewer or a later
     retraction path can always re-check the row against the exact quoted
     text).
4. **Contract-version discipline applies the same way it does to the R&R
   job-title/relationship-type field split.** Adding a new predicate to a
   closed vocabulary that flows through the extraction prompt requires a
   `POST_SUMMARY_CONTRACT_VERSION` bump and a reviewed prompt change, because
   every future extraction depends on the contract version
   (`lineageweave/post_summary.py`). That prompt change is the follow-up
   implementation work this ADR authorizes in shape but does not itself
   perform.
5. **No new organization/facility catalog row is created by this feature.**
   The organization side resolves through the existing
   `get_or_create_corporate_entity` path (ADR 0010, ADR 0026) exactly as any
   other organization mention would; a planned-facility relationship is
   never itself grounds to auto-create an ambiguous or uncorroborated
   organization. If the organization side is unresolved, the relationship
   row still records the raw actor name (as `SemanticRelationship` already
   allows via `subject_name`) — it is enrichment, not a gate on the row
   existing.

## Considered alternatives

- **A dedicated `project_operator_relationship` table / new relationship
  class.** Rejected: `post_summary_semantic_relationship` already is that
  table in shape (typed subject/object, closed predicate vocabulary,
  mandatory evidence, confidence). A parallel table would duplicate the
  schema, the ontology-annotation lookup, and the frontend rendering path
  for no behavioral gain, and would need its own migration, API surface, and
  tests that the existing channel already has.
- **Infer "operates" directly instead of "plans to operate."** Rejected:
  this is exactly the fact-invention risk the gap doc calls out. The source
  text supports a plan; asserting operation is a stronger claim the
  evidence does not carry.
- **Do nothing; leave facility mentions as unlinked prose.** Rejected: this
  is the status quo the gap doc flags as a real product gap — an
  entity-and-relationship-shaped fact in the source text is currently
  invisible to the ontology/entity graph.

## Consequences

- The implementation bumps `POST_SUMMARY_CONTRACT_VERSION`, extends the
  extraction prompt and ontology registry, and independently rechecks the
  R&R actor, project backing, facility type, and literal evidence span before
  retaining a model-emitted `lw_plans_to_operate` row. Missing evidence drops
  only that relationship; other supported semantic relationships remain.
- Because the table enforces the closed predicate vocabulary at write time,
  migration 0138 expands
  `post_summary_semantic_relationship_predicate_code_check` with
  `lw_plans_to_operate`. The Python frozenset, database constraint, and
  ontology annotation lookup therefore reject vocabulary drift at their
  respective parse, persistence, and reader boundaries.
- A downside accepted here: `lw_plans_to_operate` is a LineageWeave-local
  (`lw_*`) predicate, not a borrowed PROV-O/SKOS/ODRL term, because none of
  the already-adopted standard vocabularies (PROV-O, SKOS, DCT, SOSA, ODRL)
  has a term for an announced-but-not-yet-executed operational
  relationship. This is consistent with the existing `lw_*` namespace's
  purpose (`lw_has_goal`, `lw_has_next_step`, etc. are the same kind of
  LineageWeave-specific narrative-structure predicate already in the
  vocabulary), not a new category of exception.

## References (APA 7th)

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization
system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

W3C OWL Working Group. (2012). *OWL 2 Web Ontology Language document overview
(2nd ed.)*. World Wide Web Consortium. https://www.w3.org/TR/owl2-overview/

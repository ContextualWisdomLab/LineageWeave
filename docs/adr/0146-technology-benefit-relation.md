# ADR 0146 — A technology-transfer fact decomposes into three technology-subject semantic-relationship rows, not a new table

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

Source research (ADR 0133/0145) can already resolve a partner organization
that a post names only indirectly — for example, a labeled address
("소재지") that matches a real company. That is a real capability: the
system can say *this organization is associated with this post*. It cannot
yet say *why*. A reviewer opening a post that names a technology partner has
no structured answer to the three questions a buyer actually asks: which
technology or capability did the partner provide, which of our
organizations received it, and where do they intend to apply it? Today that
information, when the post states it explicitly, is either dropped or
buried as free-text `evidence_text` inside an unrelated relation row (or a
generic `key_event`), never surfaced as its own fact.

### What already exists that this can reuse

- `post_summary_semantic_relationship` / `SemanticRelationship`
  (`lineageweave/post_summary.py`) is the same generic, closed-vocabulary,
  evidence-required subject–predicate–object channel ADR 0142 reused for the
  planned-facility relation: `SEMANTIC_RELATION_NODE_TYPES` and
  `SEMANTIC_RELATION_PREDICATES` are closed sets; a row without a non-empty
  `evidence_text` is rejected by `SemanticRelationship.__post_init__`.
- Nothing in that vocabulary today lets the *technology itself* be the
  subject of a relation. `industrial_asset` and `industrial_process` name
  physical objects and operational processes (ISA-95 scoped); neither fits
  an abstract technology, method, or model.
- `hasVopRelationship` (Voice-of-Partner) already exists at the
  organization-to-organization level and must stay untouched: "this
  technology came from this partner" and "this organization is our
  partner" are different claims, the same separation ADR 0145 already
  drew for source-research actor recognition.

Given this, the missing piece is again not a new table: it is a new
`technology` node type plus three closed predicates that let one
technology-transfer fact decompose into up to three rows sharing the same
technology subject name, the same n-ary-fact-as-a-star pattern RDF/PROV-O
already uses for facts with more than two participants.

## Decision

1. **Reuse `post_summary_semantic_relationship`; do not add a new table or
   `SemanticAssertion` subclass.** Add one new closed node type,
   `technology` (`:Technology`, subclass of `prov:Entity`), and three new
   predicate codes to `SEMANTIC_RELATION_PREDICATES` and
   `docs/ontology/lineageweave-kg.ttl`:
   - `lw_technology_provided_by` — subject is the named technology, object
     is the providing organization.
   - `lw_technology_adopted_by` — subject is the same technology, object is
     the adopting organization.
   - `lw_technology_applied_to` — subject is the same technology, object is
     the project, facility, process, or place the adopter intends to apply
     it to (object type `project`, `industrial_asset`, `industrial_process`,
     or `place`, whichever the source names).
2. **Every row stands alone; none is required for the others to exist.** A
   post may state only that a technology was provided (no stated adopter
   yet), or only that it was adopted (source doesn't name the original
   provider), or all three. The extractor emits whichever rows the source
   text actually supports and omits the rest — mirroring how
   `lw_responsible_for` and `lw_supports` are independent, not mutually
   required.
3. **No cross-section admission gate, unlike `lw_plans_to_operate`.** ADR
   0142's planned-facility predicate needed corroboration from a separate
   ROLES/PROJECTS extraction pass because it asserts a *future* operational
   fact from event-adjacent context. A technology-provided/adopted/applied
   statement is normally a directly stated fact in the same sentence
   ("adopted the diagnostics model from AcmeTech"), so it is admitted the
   same way `org_member_of` or `lw_responsible_for` are: a single row with
   its own literal `evidence_text` and `confidence` is sufficient.
4. **Structural validation lives in `SemanticRelationship.__post_init__`.**
   Any row using one of the three technology predicates must have
   `subject_type == "technology"`; this is enforced in code (not only by
   prompt instruction) so a model swapping subject/object cannot silently
   produce an unqueryable row.
5. **Contract-version discipline applies.** Adding predicates to a closed
   vocabulary that flows through the extraction prompt requires the same
   `POST_SUMMARY_CONTRACT_VERSION` bump and reviewed prompt change every
   prior predicate addition required.

## Considered alternatives

- **Model the technology as a fourth argument on one row instead of a
  separate node.** Rejected: `SemanticRelationship` is a strict binary
  (subject, predicate, object) triple by design; adding a fourth free-text
  argument would special-case this one predicate family, break the existing
  "every relation is a triple" invariant every renderer and test relies on,
  and still not let the technology be independently referenced from a
  fourth fact later (e.g. a future "same technology, different post" join).
- **Reuse `industrial_asset` or `industrial_process` for the technology
  node instead of adding `technology`.** Rejected: both classes are
  explicitly ISA-95/OPC-UA scoped to physical equipment and operational
  process (see their `rdfs:comment` in the ontology). Forcing an abstract
  method or model into either misrepresents the fact and would corrupt
  any future ISA-95-grounded reasoning over those two classes specifically.
- **A single `lw_technology_transfer_from` organization-to-organization
  predicate, with the technology name left in `evidence_text`.** Rejected:
  this is exactly the status quo gap — it answers "who" but keeps "what
  technology" and "applied where" as unstructured prose, which is what a
  buyer-facing UI cannot render as distinct facts.

## Consequences

- The implementation bumps `POST_SUMMARY_CONTRACT_VERSION`, extends the
  extraction prompt with usage guidance and fictional examples for the
  three predicates, and adds the `technology` node type and predicate
  entries to the ontology's `SemanticPredicateMapping` list (read at
  request time by `semantic_predicate_annotations`).
- Migration 0177 extends the existing write-time `subject_type`,
  `object_type`, and `predicate_code` checks on
  `post_summary_semantic_relationship`; the ontology annotation lookup
  remains the read-time IRI/label projection, same boundary ADR 0142 used
  for migration 0138.
- A downside accepted here, same as ADR 0142: all three predicates are
  LineageWeave-local (`lw_*`), not borrowed PROV-O/SKOS/ODRL terms, because
  none of the already-adopted standard vocabularies has a term for
  "provided this named technology" specifically distinct from generic
  `prov:wasAssociatedWith`. This is consistent with the existing `lw_*`
  namespace's purpose.

## References (APA 7th)

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization
system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

W3C OWL Working Group. (2012). *OWL 2 Web Ontology Language document overview
(2nd ed.)*. World Wide Web Consortium. https://www.w3.org/TR/owl2-overview/

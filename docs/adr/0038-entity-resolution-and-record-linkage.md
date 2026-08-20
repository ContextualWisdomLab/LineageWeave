# ADR 0038 — Entity resolution and record linkage as first-stage blocking and similarity, not full collective inference

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

LineageWeave has two places where records or named organizations must be
treated as the same real-world thing, or left unresolved:

1. **Record-to-record lineage.** `reconstruct.py` groups records by a
   coarse `group_key` (account, customer, or similar), then scores each
   later record against a backward temporal window of candidates. A
   finer key -- `Record.secondary_key`, typically a project code -- is
   an independent same-thread signal. The research notes already treat
   that key as a coarse blocking key in the Fellegi & Sunter (1969) /
   Christen (2012) record-linkage sense
   (`docs/lineage-bi-research-notes.md`, Channels table). Until this
   ADR there was no dedicated decision record for that choice, or for
   how far the product actually implements the linkage literature.
2. **Free-text organization names.** Keyman affiliations and
   entity-relationship classification both need to attach a mentioned
   string ("Acme Elec Korea", "Acme Electronics Korea Ltd.") to an
   existing `corporate_entity` row. Exact string match misses the
   abbreviations and legal suffixes that show up in short records.
   `lineageweave/corporate_hierarchy_resolution.py` already implements
   normalized-name similarity against cataloged candidates and returns
   `None` when nothing clears the threshold. The research notes ground
   that module in Bhattacharya & Getoor (2007) and already say it is
   the first stage of collective entity resolution, not the full
   joint-inference version. That scope also had no ADR.

These are related decisions: both refuse to invent a link when the
evidence is weak, and both stop at the cheap, inspectable first stage
of the literature rather than claiming a full probabilistic matcher or
a joint collective resolver.

## Decision

Use the standard first stages of record linkage and collective entity
resolution, implemented as two existing modules, and do not claim the
later stages those papers also describe.

**Blocking / agreement on a secondary key (Fellegi & Sunter, 1969;
Christen, 2012).** Fellegi and Sunter's theory of record linkage
compares pairs on agreement patterns and decides match / non-match /
clerical review. Practically, every linkage pipeline still starts by
*blocking*: only pairs that share a cheap, coarse key are compared, so
the search does not become all-pairs (Christen, 2012, on blocking,
comparison, and classification as the usual stages). LineageWeave
applies that first-stage idea, not the full Fellegi–Sunter decision
rule:

- `group_key` is the hard partition -- a record is never a candidate
  parent of a record in a different group (`reconstruct._group_by`).
- Inside a group, only the most recent `DEFAULT_CANDIDATE_WINDOW`
  earlier records are scored (a temporal block, not an all-pairs
  comparison).
- `secondary_key` is the finer blocking-style agreement signal:
  `channels.secondary_key_match_score` returns 1.0 when both sides
  share a non-empty key and 0.0 otherwise. It is fused with temporal,
  text, and optional LLM channels (`reconstruct.DEFAULT_CHANNEL_WEIGHTS`),
  not used as a hard exclude. An empty key is "no signal," not a
  confident non-match -- the same missing-vs-negative distinction this
  repo already uses for pluggable channels.

This is not a Fellegi–Sunter matcher. There are no estimated m/u
agreement probabilities, no composite match weight from a comparison
vector, and no three-way match / possible / non-match clerical band.
The analog of "leave it unresolved" is `DEFAULT_MIN_FUSED_SCORE`:
below the floor a record stays its own root rather than being
force-attached to the least-bad candidate.

**Candidate generation and similarity scoring (Bhattacharya & Getoor,
2007).** Collective entity resolution argues that ambiguous references
are best resolved using relational context -- which other entities
co-occur with this mention -- not string similarity in isolation.
Bhattacharya and Getoor still need a first stage that generates
candidates and scores them. `corporate_hierarchy_resolution` is that
stage:

- Normalize both the mention and each cataloged `corporate_entity`
  name (lowercase, strip punctuation and common legal suffixes, collapse
  whitespace).
- Score with `difflib.SequenceMatcher` ratio.
- Return the best candidate's id if it clears `DEFAULT_MIN_SIMILARITY`
  (0.6); otherwise return `None`.

`None` is a first-class outcome. A wrong hierarchy link corrupts every
downstream Knowledge Graph walk through that node (affiliate tree,
related-node traversal, VOC evidence). Keyman ingestion and
entity-relationship ingestion both persist an unresolved name as text
with a null `corporate_entity_id` rather than guessing.

This is honestly the *first* stage of what Bhattacharya & Getoor call
collective resolution, not the full joint-inference version. A
genuinely collective resolver would also weigh which other
organizations and people are co-mentioned in the same post against
each candidate's known affiliates, and could resolve two different
ambiguous mentions in one post jointly. That joint step is a
documented upgrade path, not implemented here, because nothing in this
product's usage has shown single-mention similarity scoring under- or
over-resolving. The research notes already state this limit; this ADR
records it as the product decision.

## Consequences

- Lineage reconstruction stays a fused multi-channel score over a
  blocked candidate window. Adding a full Fellegi–Sunter weight model
  or a clerical-review queue would be a new decision, not a silent
  reinterpretation of `secondary_key`.
- Organization resolution stays independent per mention. Adding
  joint/collective inference (co-mention and affiliate-graph evidence)
  would be a new decision, not a silent upgrade of
  `resolve_corporate_entity`.
- Callers must keep treating `None` / own-root as real outcomes. UI
  and persistence already do this (unresolved names stay text; weak
  lineage edges are not written).
- The literature register in `docs/lineage-bi-research-notes.md`
  remains the in-text (name, year) home for these papers; this ADR is
  the decision record. In-text citations there stay name+year as long
  as that References section stays complete.

## Related

Builds on the channel set and corporate-hierarchy writeup in
[`docs/lineage-bi-research-notes.md`](../lineage-bi-research-notes.md)
(Channels table; "Entity-relationship classification and corporate
hierarchy resolution"). The resolved `corporate_entity` rows this
module attaches to are the same SKOS-modeled hierarchy
[ADR 0004](0004-knowledge-graph-ontology.md) publishes. Relation
labels on those entities are a separate inference, verified
(existence/plausibility only) by
[ADR 0005](0005-relation-verification-agent.md).

## References (APA 7th)

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, *1*(1), 5-es. https://doi.org/10.1145/1217299.1217304

Christen, P. (2012). *Data matching: Concepts and techniques for record linkage, entity resolution, and duplicate detection*. Springer. https://doi.org/10.1007/978-3-642-31164-2

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal of the American Statistical Association*, *64*(328), 1183–1210. https://doi.org/10.1080/01621459.1969.10501049

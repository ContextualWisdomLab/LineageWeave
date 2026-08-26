# ADR 0247: Evidence-bearing Voice-of-X combinations

## Status

Accepted (2026-08-27). Extends ADR 0246 without replacing the imported
`source_post.voc_type_code` contract.

## Context

A record can carry more than one stakeholder perspective: for example, a
customer-authored record can preserve a downstream user's statement, or an
employee can report a process-generated signal. Encoding every pair or larger
combination as a new lookup code creates an unbounded Cartesian vocabulary and
loses the evidence for each component.

No cited standard defines a finite, universal list of stakeholder
combinations. ISO stakeholder guidance explicitly allows the relevant
categories to vary by subject. ISO 26000 and AA1000SES instead require ongoing,
context-sensitive stakeholder identification and engagement. Mitchell, Agle,
and Wood (1997) likewise derive stakeholder salience from combinations of
attributes rather than from one exhaustive industry-role list.

## Decision

Represent composition as rows in normalized `source_post_voice`, not as
compound lookup codes.

- The existing `source_post.voc_type_code` remains the authoritative imported
  primary voice. A trigger mirrors it into exactly one primary association so
  existing import, filtering, and lineage behavior remains stable.
- An additional voice uses another existing `voc_type` code and must reference
  a normalized `provenance_assertion`. Missing evidence therefore cannot be
  persisted as a positive association.
- The pair `(post_id, voice_type_code)` is unique. One partial unique index
  permits only one primary voice while allowing any evidence-backed subset of
  the governed vocabulary as additional voices.
- A database trigger verifies that every association code belongs to the
  `voc_type` lookup category and every truth code belongs to
  `ontology_truth_status`;
  the global lookup-code foreign key alone does not establish either category
  boundary. Promoting an existing additional voice to the imported primary
  resets it to observed source evidence and removes the now-unneeded derived
  assertion reference.
- Voice remains distinct from counterparty relationship, actor role, topic,
  channel, lifecycle, and stakeholder-salience attributes. No inference,
  keyword rule, confidence threshold, or weight converts those dimensions into
  a voice.
- The public ontology represents each row as a qualified `VoiceAssignment`
  linked from its post. Each assignment names one atomic SKOS voice concept;
  additional assignments retain evidence through `prov:wasDerivedFrom`.
- Authorized post list/detail responses expose ordered voice assignments with
  labels, truth state, and evidence availability but never internal assertion
  identifiers. Filters match any associated voice, and repeated post cards show
  the combined labels.
- The authorized ontology neighborhood projects each association as a
  qualified assignment in JSON-LD and the exact-value CSV. SHACL requires its
  atomic voice concept, primary flag, and source-post evidence. The exact-value
  table opens that already-authorized source post; it does not invent a graph
  edge or expose an internal assertion identifier.

## Data model

```mermaid
classDiagram
  class SourcePost {
    uuid post_id
    text voc_type_code
  }
  class SourcePostVoice {
    uuid post_id
    text voice_type_code
    boolean is_primary
    text truth_status_code
    uuid provenance_assertion_id
    timestamptz recorded_at
  }
  class LookupValue {
    text lookup_code
    text lookup_category
  }
  class ProvenanceAssertion {
    uuid assertion_id
  }
  SourcePost "1" --> "1..*" SourcePostVoice
  LookupValue "1" --> "0..*" SourcePostVoice
  ProvenanceAssertion "0..1" --> "0..*" SourcePostVoice
```

## Consequences

Migration 0237 is replay-safe, backfills one primary association per existing
post, synchronizes later inserts and primary-voice changes, and adds a
voice-first index for bounded filtering. It introduces no new Voice-of-X
category and stores no source content or identifying evidence in repository
artifacts.

The repository candidate projects authorized combinations through JSON-LD,
SHACL, CSV, and evidence navigation. Its synthetic Storybook desktop/mobile
scene verifies a focused evidence action and a contained horizontally
scrollable exact-value table. Authenticated runtime and an authorized write
workflow for additional assignments remain required before a release claim.

## References

AccountAbility. (2015). *AA1000 stakeholder engagement standard*.
https://www.accountability.org/standards/aa1000-stakeholder-engagement

International Organization for Standardization. (2010). *Guidance on social
responsibility* (ISO Standard No. 26000:2010).
https://www.iso.org/standard/42546.html

International Organization for Standardization. (2023, December 19).
*Global Directory stakeholder categories*.
https://helpdesk-docs.iso.org/article/331-gd-stakeholders-categories

Mitchell, R. K., Agle, B. R., & Wood, D. J. (1997). Toward a theory of
stakeholder identification and salience: Defining the principle of who and
what really counts. *Academy of Management Review, 22*(4), 853–886.
https://doi.org/10.5465/amr.1997.9711022105

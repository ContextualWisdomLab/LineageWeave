# ADR 0006 — R&R's named actor is a PROV-O Agent, not always a person

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

The product brief flags a real gap in `post_summary.py`'s R&R (roles &
responsibilities) extraction, confirmed against real SAP CRM VOC records
during Milestone 2 analysis: the acting party a post's text names is not
always a person. Real business correspondence routinely names an
organization acting in its own name -- "당사" (our company), "SEWA,"
"Siemens," "GECO" -- not a named individual. The brief's own wording:
"주체가 사람이 아니라 기관 ... 으로 나타나는 경우도 있으므로 일반적인
표준 Ontology로 조치할 것" (the acting subject sometimes appears as an
organization rather than a person, so handle it with a general standard
Ontology), plus "사람만 넣어서는 소속 기관을 이해하기 어려우므로 소속
기관 추론까지 포함시킬 것" (a bare person name is hard to place without
their organization, so infer the affiliation too).

Before this change, `RoleResponsibility.person_name` had no way to
express "this actor is an organization" -- every entry was forced into
a person slot, and an organization actor's name would sit
indistinguishable from an unresolved person.

## Decision

Ground the distinction in W3C PROV-O (Lebo, Sahoo, & McGuinness, 2013):
`prov:Agent` is the general acting-party class, with `prov:Person` and
`prov:Organization` as its two recognized subclasses -- an existing,
widely-adopted standard for exactly this "who/what acted" provenance
question, not a bespoke local invention.

`RoleResponsibility` (`lineageweave/post_summary.py`) gains:
- `actor_name` (renamed from `person_name` -- the field can now hold an
  organization's name too, so "person" in the field name would be
  actively wrong).
- `actor_type_code`: `prov_person` / `prov_organization`
  (`common_lookup_value` category `prov_agent_type`), defaulting to
  `prov_person` when the LLM's response omits the field, matching this
  repo's existing degrade-gracefully-not-fail discipline.
- `affiliated_organization_name`: for a person actor, the organization
  the text names or clearly implies they work for, inferred by the same
  LLM call rather than left for a human to cross-reference against the
  Keyman panel separately. `None` when the text gives nothing to infer,
  or when the actor is itself an organization (its own name already
  answers "which organization").

The LLM prompt now explicitly instructs the model to decide
person-vs-organization per actor rather than defaulting every named
actor to a person, and to give an affiliation when the text supports
one.

Ontology (`docs/ontology/lineageweave-kg.ttl`, extending
[ADR 0004](0004-knowledge-graph-ontology.md)'s vocabulary):
`:RoleActorPerson rdfs:subClassOf prov:Person` and
`:RoleActorOrganization rdfs:subClassOf prov:Organization`, each
carrying the `:lookupCode` annotation linking it to the matching
`common_lookup_value` row -- these are genuinely subclasses of the real
external PROV-O classes (imported via the `prov:` prefix), not
same-named local terms that merely resemble the standard. Kept distinct
from the ontology's existing `:Person` (node_type's `node_person`,
i.e. a cataloged Keyman with a stable `person_id`): an R&R actor is a
free-text name with no cataloged identity of its own, and may not even
resolve to a Keyman row.

Persistence: `post_summary_role` gains `actor_type_code` (FK to
`common_lookup_value`, default `prov_person`) and
`affiliated_organization_name`; `person_name` is renamed to
`actor_name` via `migrations/0012_role_responsibility_agent_type.sql`'s
`ALTER TABLE ... RENAME COLUMN` (preserves every existing row's data,
unlike a drop/recreate) plus the two new `ADD COLUMN IF NOT EXISTS`
statements, with `migrations/0001_initial_schema.sql` updated directly
for a fresh install, matching this repo's established pattern (e.g.
ADR 0005's `verification_status_code` additions).

UI: the popup's R&R list (`frontend/src/App.tsx`) shows a
Person/Organization badge per actor and the inferred affiliation in
parentheses; only a person actor is still linked to the Keyman panel
(an organization actor has no `person_id` to link to).

## Consequences

- `RoleResponsibility.person_name` is a breaking rename to `actor_name`
  across the JSON wire contract (`GET /api/posts/{id}/summary`), the
  DB column, and every call site. Accepted because the field's old name
  was actively misleading once an organization actor is a real,
  intended value, not a hypothetical edge case -- confirmed against
  real Milestone 2 SAP CRM VOC data.
- `prov_agent_type` is a `common_lookup_value` category seeded by its
  own migration file (0012), not literally embedded in
  `scripts/seed_demo_data.py`'s SQL string the way ADR 0004's original
  five covered categories are -- `tests/test_ontology.py`'s round-trip
  check reads 0012's file content alongside the seed script's own text
  so this still closes the loop, rather than being silently excluded
  the way `evaluation_criterion` / `relation_verification_status`
  currently are.
- The affiliation inference is opportunistic, not authoritative: it is
  a same-request LLM guess from the post's own text, not resolved
  against `corporate_entity` the way Keyman affiliations are (see
  `lineageweave/corporate_hierarchy_resolution.py`). A future slice
  could route it through the same resolver if real usage shows the
  free-text name needs matching back to a cataloged organization.

## Related

Extends [ADR 0004](0004-knowledge-graph-ontology.md)'s Ontology/
Semantic-Layer vocabulary and reuses its round-trip enforcement
mechanism (`tests/test_ontology.py`).

## References (APA 7th)

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

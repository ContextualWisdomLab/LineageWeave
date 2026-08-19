# ADR 0007 — R&R's named actor can be a team, a meso-level unit, not just a person/organization

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

ADR 0006 gave R&R's `actor_type_code` two values: `prov_person` and
`prov_organization`, grounded in W3C PROV-O's `prov:Agent` subclasses.
Real post text surfaced a third, distinct case those two do not cover:
a named sub-unit of a company -- e.g. "설계팀" (design team) -- acting
in the text. A team is not a person, and forcing it into
`prov_organization` is wrong for the same reason ADR 0006 rejected
forcing an organization into a person slot: it collapses a real,
useful distinction. A team is meso-level -- part of a company, not the
company itself, and not an individual either.

PROV-O has no sub-organization concept to reuse here; `prov:Agent`'s
two subclasses are exhaustive for PROV-O's own purposes (an
organization's internal structure is out of PROV-O's scope).

## Decision

Ground the team case in the W3C Organization Ontology (Reynolds, 2014):
`org:OrganizationalUnit`, defined for exactly this -- representing the
division of an organization into sub-organizational units, linked to
its parent via `org:unitOf`/`org:subOrganizationOf`. This is a
different, complementary W3C vocabulary from PROV-O, not a conflicting
one: PROV-O models "who/what acted," ORG models "how an organization is
structured internally" -- a team acting in a post's text needs both a
`prov:Agent`-shaped role (it does something) and an
`org:OrganizationalUnit`-shaped identity (it belongs to a company).
`:RoleActorTeam` is declared `rdfs:subClassOf org:OrganizationalUnit`
for that reason, parallel to how `:RoleActorPerson`/
`:RoleActorOrganization` subclass PROV-O's classes.

`post_summary.py` gains `ACTOR_TYPE_TEAM = "prov_team"`
(`common_lookup_value` category `prov_agent_type`, extending ADR
0006's two existing values). The LLM prompt now offers three actor
types (person / organization / team) and explicitly requires a team
actor to also carry `affiliated_organization_name` -- unlike an
organization actor (whose own name already answers "which
organization"), a team's name alone does not identify a company, so
the field is not optional in the same "opportunistic" sense ADR 0006
described for a person actor; a team is always someone's team, and the
prompt asks the model to infer the parent company from context when
the text supports it.

No new `RoleResponsibility` field is needed:
`affiliated_organization_name` already exists (ADR 0006) and applies
unchanged to this actor type -- only its *meaning* extends from
"the person's employer" to "the person's or team's parent
organization," which the dataclass docstring now says explicitly.

Persistence: `migrations/0014_role_responsibility_team_actor_type.sql`
inserts the `prov_team` lookup row -- purely additive
(`insert ... on conflict (lookup_code) do nothing`), no column or
constraint change, since `actor_type_code` already stores an arbitrary
FK'd lookup code and needs no schema change to accept a third value.

## Consequences

- `_VALID_ACTOR_TYPE_CODES` in `post_summary.py` now has three members;
  any code elsewhere that pattern-matches strictly on the first two
  (rather than treating an unrecognized/future code as "not this one")
  needs review. Found and fixed one: the frontend badge's CSS class name
  (`actor-type-${code}`) was already generic, but its *label text* was a
  binary person/organization ternary that would have mislabeled a team
  actor as "Organization" -- now a three-way check.
- A team actor is never linked to the Keyman panel (same as an
  organization actor in ADR 0006) -- it has no `person_id`.
- Distinguishing "설계팀" (a team) from "Design Corp" (an organization)
  is a real LLM judgment call with no hard syntactic rule; the prompt
  gives the model the concept and an example, matching this repo's
  existing degrade-gracefully discipline for judgment-call extraction
  fields (a wrong guess is a labeling error on one row, not lost data --
  the raw `actor_name` string is preserved regardless of which type it
  is filed under).

## Related

Extends [ADR 0006](0006-role-responsibility-agent-ontology.md), which
itself extends [ADR 0004](0004-knowledge-graph-ontology.md)'s Ontology/
Semantic-Layer vocabulary.

## References (APA 7th)

Reynolds, D. (Ed.). (2014). *The organization ontology* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/vocab-org/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

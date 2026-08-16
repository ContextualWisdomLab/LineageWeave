# ADR 0014 — Related-node chips distinguish plural affiliations from missing ones

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

Related-node person chips may carry at most one compact organization
name. The `person_affiliation` schema is multiple-membership: a person
can belong to several organizations at once, and the table has no
`primary` column. Collapsing that set by sort order invents a primary
the buyer cannot authorize.

v0.75.0 therefore omitted the organization whenever more than one
distinct identity remained. That avoided a false primary, but it also
made a known-plural set look identical to a person with no affiliation.
A missing signal and a confidently-plural signal are different things
(see `AGENTS.md`). The buyer could not tell whether to open the Keyman
panel for a full affiliation list.

Multiple-membership models treat those memberships as simultaneous, not
as a ranked primary plus leftovers (Browne et al., 2001). ISO 9241-110
requires dialogue that does not hide the state the user needs for the
next action (International Organization for Standardization, 2020).

## Decision

Hydrate emits:

- `affiliation_organization_name` only when exactly one distinct
  organization identity remains after catalog-id and casefold-alias
  collapse;
- `affiliation_ambiguous: true` when more than one identity remains,
  with no organization name.

The chip caption for a plural set is
`{name}, multiple organizations ({side})`. That name is not an
organization. The next action is to open the Keyman / affiliate
surface, which already lists every authorized affiliation.

Unresolved extraction strings that differ only by letter case count as
one identity. Distinct unresolved names, or a catalog org plus a
different unresolved name, stay plural.

## Consequences

After `make seed`, Priya Nair (Northridge Grid and Northridge Holdings)
reads `Priya Nair, multiple organizations (Counterparty)`. Ada West
(Demo Corp only) still reads `Ada West, Demo Corp (Our side)`. A person
with no affiliation row stays side-only.

## References

Browne, W. J., Goldstein, H., & Rasbash, J. (2001). Multiple membership
multiple classification (MMMC) models. *Statistical Modelling, 1*(2),
103–124. https://doi.org/10.1177/1471082X0100100202

International Organization for Standardization. (2020). *Ergonomics of
human-system interaction — Part 110: Interaction principles*
(ISO 9241-110:2020). https://www.iso.org/standard/75258.html

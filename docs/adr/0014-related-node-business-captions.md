# ADR-0014: Related-node chips use business context, not ontology class

- Status: Accepted
- Date: 2026-08-16

## Context

Related-node chips in the Keyman walk showed the ontology class
(`Person`, `Organization`, `Post`). Buyers already know they clicked a
person or an organization. The class label does not tell them which
side the person is on, which company they represent, or what to click
next. Keyman list rows already expose `person_side_label` and every
affiliation. The compact related-node chip is a different surface: it
must stay short enough to scan while walking.

`person_affiliation` is N:N and has no `primary` column. Sorting
affiliations and taking the first row would invent a primary
organization. Priya Nair in the synthetic fixture belongs to both
Northridge Grid and Northridge Holdings.

## Decision

Hydrate related-node payloads with authorized lookup labels:

- Person chips use `person_side_label` (fallback: raw `person_side_code`).
- A person chip adds `affiliation_organization_name` only when exactly
  one distinct organization identity is known. A resolved catalog org
  supplies `corporate_entity.entity_name`; unresolved aliases that
  casefold-match that label collapse into it. Two unresolved names
  that differ only by letter case count as one identity.
- A known-plural set (two unresolved names, two catalog orgs, or a
  catalog org plus a distinct unresolved name) sets
  `affiliation_ambiguous` and the caption uses
  `multiple organizations`. That is not the same as a missing
  affiliation. The related panel then names the next action: read
  every organization in the Keyman list (or extract Keymen if the
  list is empty), then click the chip to continue the walk. The
  caption prefers the plural signal if a name is also present so a
  stale payload cannot invent a primary.
- A unique org without a side still names the org
  (`Ada West, Demo Corp`) so a missing side cannot revive the
  ontology-class caption.
- Organization chips use `entity_level_label` (fallback: raw code).
- Post chips show the post title only.

Person and organization chips use `Related nodes for ${caption}` as
the accessible name. Post chips use `Open related post: ${caption}`
so the next action stays in the name and the visible caption is
contained (WCAG 2.5.3). Full affiliation lists stay on the Keyman
and affiliate-tree surfaces.

## Consequences

Walking from Ada West shows
`Priya Nair, multiple organizations (Counterparty)` rather than
`Priya Nair, Northridge Grid (Counterparty)` or a side-only chip that
looks like Priya has no organization. Walking from Demo Corp shows
`Ada West, Demo Corp (Our side)` and `Demo Corp (Company)`.
Click a chip to continue the walk. When the chip says multiple
organizations, read the Keyman list above first.

## References

See [RELATED_NODE_AFFILIATION_REFERENCES.md](../doctoring/RELATED_NODE_AFFILIATION_REFERENCES.md).

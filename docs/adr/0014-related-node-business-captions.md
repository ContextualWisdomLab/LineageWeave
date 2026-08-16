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
  one distinct non-empty affiliation is known.
- Organization chips use `entity_level_label` (fallback: raw code).
- Post chips show the post title only.

The same caption is the interactive control's accessible name. Full
affiliation lists stay on the Keyman and affiliate-tree surfaces.

## Consequences

Walking from Ada West shows `Priya Nair (Counterparty)` rather than
`Priya Nair, Northridge Grid (Counterparty)`. Walking from Demo Corp
shows `Ada West, Demo Corp (Our side)` and `Demo Corp (Company)`.
Click a chip to continue the walk. Open the Keyman list when you need
every affiliation.

## References

Browne, W. J., Goldstein, H., & Rasbash, J. (2001). Multiple membership
multiple classification (MMMC) models. *Statistical Modelling, 1*(2),
103–124. https://doi.org/10.1177/1471082X0100100202

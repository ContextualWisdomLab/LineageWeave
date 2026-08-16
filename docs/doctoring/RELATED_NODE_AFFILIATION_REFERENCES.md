# Related-node affiliation references

APA 7th citations for ADR-0014 (compact related-node captions) and the
proposed temporal-validity follow-up. These are the sources to open
before changing affiliation display or `person_affiliation` columns.

## Multiple membership (do not invent a primary)

Browne, W. J., Goldstein, H., & Rasbash, J. (2001). Multiple membership
multiple classification (MMMC) models. *Statistical Modelling, 1*(2),
103–124. https://doi.org/10.1177/1471082X0100100202

A person can belong to several organizations at once. Sorting
`person_affiliation` and taking the first row would treat a
multiple-membership structure as if one org were the atom. Compact
chips therefore name an organization only when exactly one identity
remains, and they say `multiple organizations` when more than one
remains.

## Accessible name contains the visible caption

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

Success Criterion 2.5.3 Label in Name: the visible chip text is
contained in `Related nodes for ${caption}` or
`Open related post: ${caption}`.

## Design tokens for repeating walk controls

W3C Design Tokens Community Group. (2025). *Design Tokens Format
Module* (Editor's Draft). https://www.w3.org/community/design-tokens/

Repeating related-node chips share `--related-node-*` tokens in
`frontend/src/relatedNodeTokens.css` and the `RelatedNodeChip` module.
Do not restyle one walk surface with a one-off class.

## Time (proposed; not on this schema yet)

Singer, J. D., & Willett, J. B. (2003). *Applied longitudinal data
analysis: Modeling change and event occurrence*. Oxford University
Press.

A past affiliation that has ended is not a current second membership.
Until `person_affiliation` stores an interval, compact chips count
every stored row. Do not add those columns until Milestone 2.1
(`0012+`) and the #74 ontology stack settle migration numbers. See
[ADR-0015](../adr/0015-affiliation-validity-interval.md).

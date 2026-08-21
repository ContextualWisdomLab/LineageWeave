### Fixed

- Customer Master now preserves the authorized Group → Company → Plant hierarchy while promoting
  missing-parent, self-parent, and cyclic relations to visible `unresolved` roots instead of silently
  dropping those customers.
- Customer hierarchy rendering now follows the ontology's W3C ORG containment and separate SKOS level
  classification instead of conflating organization instances with taxonomy concepts.
- Late related-post responses can no longer replace evidence for a newly selected customer entity.

### Accessibility

- Added a reusable WAI-ARIA customer tree with one roving focus target, branch expansion,
  Arrow/Home/End navigation, Enter/Space evidence activation, exact level/position metadata, and an
  independently owned source-post evidence panel.

# Customer hierarchy standards and research traceability

**Decision:** ADR 0124 — Cycle-safe customer master tree projection  
**Reviewed:** 2026-08-21  
**Figma file ID:** `SBpgot7uTvMxEaxUwvoc0S`

## Traceability

| External source | Product decision | Implementation evidence | Current limitation |
|---|---|---|---|
| W3C Organization Ontology | Real corporate entities are `org:Organization` instances; `parent_entity_id` projects through `subOrganizationOf`, a specialization of `org:subOrganizationOf`. | `docs/ontology/lineageweave-kg.ttl`, `tests/test_ontology_interoperability.py` | One parent context only; no effective-dated legal/operating hierarchy contexts yet. |
| W3C SKOS | Group, Company, and Plant are classification concepts, not the real customer organizations. | `CorporateEntityLevel`, `hasEntityLevel`, and level concepts in the ontology | Allowed level-transition rules are not yet encoded. |
| W3C SHACL | Closed-world validation requires exactly one level and at most one parent in the published projection. | `docs/ontology/lineageweave-kg.shacl.ttl`, ontology interoperability tests | Global acyclicity is not yet a SHACL constraint; the buyer projection therefore remains defensive. |
| WAI-ARIA APG Tree View Pattern | Use `tree`, nested `treeitem`/`group`, roving focus, Arrow/Home/End navigation, and branch `aria-expanded`. | `CustomerMasterTree.tsx` and component tests | Type-ahead navigation is not included in this bounded change. |
| WCAG 2.2 | All hierarchy and evidence actions are keyboard operable with a visible focus target and preserve the current selection. | Component keyboard tests and existing focus design tokens | Full assistive-technology browser acceptance remains a release-level check. |

## Product truth boundary

The ontology and SHACL graphs describe and validate the relational projection; PostgreSQL remains the
source of record. The browser never writes a repaired parent relation. Missing-parent, self-parent, or
cyclic edges are displayed as `unresolved` roots so an authorized customer cannot disappear and a
replacement parent is not invented.

## References — APA 7th

World Wide Web Consortium. (2009). *SKOS simple knowledge organization system reference*.
https://www.w3.org/TR/skos-reference/

World Wide Web Consortium. (2014). *The Organization Ontology*.
https://www.w3.org/TR/vocab-org/

World Wide Web Consortium. (2017). *Shapes Constraint Language (SHACL)*.
https://www.w3.org/TR/shacl/

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*.
https://www.w3.org/TR/WCAG22/

World Wide Web Consortium, Web Accessibility Initiative. (n.d.). *Tree view pattern*.
https://www.w3.org/WAI/ARIA/apg/patterns/treeview/

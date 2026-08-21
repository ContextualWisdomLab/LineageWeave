# ADR 0124: Cycle-safe customer master tree projection

- **Status:** Accepted
- **Date:** 2026-08-21
- **Owners:** Buyer surface and ontology projection
- **Figma file ID:** `SBpgot7uTvMxEaxUwvoc0S`

## Context

`GET /api/customer-master` returns the authorized corporate-entity projection as a flat array with
`parent_entity_id`. The buyer surface previously rebuilt a nested list directly in `App.tsx`.
That recovered ordinary Group → Company → Plant relationships, but it had three product defects:

1. a self-parent or multi-node cycle had no root and therefore disappeared from the customer master;
2. `aria-expanded` described whether related posts were open, not whether the hierarchy branch was
   expanded; and
3. the nested list did not implement the keyboard and focus behavior required by the WAI-ARIA tree
   pattern.

The ontology now correctly separates real organization instances from their classification levels:

- `CorporateEntity` specializes `org:Organization`;
- `subOrganizationOf` is the semantic projection of `corporate_entity.parent_entity_id` and
  specializes `org:subOrganizationOf`;
- `hasSubOrganization` is its inverse;
- Group, Company, and Plant are `CorporateEntityLevel` SKOS concepts selected by `hasEntityLevel`;
- the SHACL profile requires exactly one level and no more than one parent in this projection.

An entity authorized for the caller must not disappear because an imported hierarchy edge is malformed
or because its parent is outside the caller's visible scope. At the same time, the browser must not
invent a replacement parent or promote an inferred relation to an authoritative ontology fact.

The W3C Organization Ontology supplies organizational containment. SKOS supplies the separate level
classification. SHACL supplies closed-world cardinality checks. The WAI-ARIA Authoring Practices Tree
View Pattern defines `tree`, `treeitem`, `group`, branch `aria-expanded`, roving focus, and arrow-key
navigation for an interactive hierarchy.

## Decision

1. Keep PostgreSQL `corporate_entity.parent_entity_id` as the authority. The ontology and SHACL graphs
   are semantic and validation projections, not a second writable hierarchy.
2. Preserve the current ontology boundary: organization containment uses W3C ORG; Group/Company/Plant
   level classification uses SKOS. Do not use `skos:broader` between real company instances.
3. Move browser hierarchy assembly into `frontend/src/customerMasterTree.ts`.
4. Preserve API order for roots and siblings and preserve every unique authorized entity.
5. Keep a parent link only when the parent is present in the authorized response.
6. Promote a missing-parent, self-parent, or every member of a detected cycle to a visible root and
   mark the relation `unresolved`; do not infer a replacement parent.
7. Render the projection through the reusable `CustomerMasterTree` component.
8. Separate hierarchy disclosure from evidence disclosure:
   - Left/Right Arrow collapses, expands, and moves to parent or first child.
   - Up/Down Arrow, Home, and End move through visible tree items.
   - Enter or Space selects an entity and opens source-backed related posts.
   - Related-post evidence is rendered outside the `tree` ownership boundary.
9. Explicitly declare `aria-level`, `aria-posinset`, and `aria-setsize`; use one roving `tabIndex=0`
   and `aria-selected` for the entity whose evidence is open.
10. Reject stale related-post responses after the buyer selects another entity.
11. Keep the current flat API as a bounded authorized projection. Legal ownership, operating
    structure, sales roll-up, billing structure, and historical hierarchy remain a later normalized,
    effective-dated relation model.

## Consequences

### Positive

- Ordinary Group → Company → Plant structures remain visibly hierarchical.
- Real organization instances and SKOS classification concepts remain semantically distinct.
- Malformed or partially visible relations are reviewable instead of silently omitted.
- Keyboard and screen-reader users receive a real tree interaction model.
- Related-post evidence cannot introduce non-tree roles inside the tree ownership boundary.
- The component is independently testable and represented in Storybook.
- Related-post evidence remains source-backed, lazy-loaded, and stale-response safe.

### Trade-offs

- An unresolved relation is shown at the root level, which is intentionally less specific than
  guessing a parent.
- Client-side defensive projection does not repair the authoritative data. Operators still need a
  data-quality workflow for cyclic or invalid source relations.
- The current SHACL profile constrains cardinality and class, but it does not yet prove global
  acyclicity or allowed level transitions.
- The referenced Figma file does not contain a dedicated public customer-tree frame. This change uses
  the existing design-token and Storybook boundary rather than claiming pixel equivalence to a
  nonexistent frame.

## Verification

- Existing ontology interoperability tests require ORG organization containment, separate SKOS level
  concepts, stable imports/versioning, and SHACL parent/level cardinalities.
- Pure frontend tests cover a three-level hierarchy, missing parent, self-parent, multi-node cycle,
  descendant preservation, ordering, and collapsed navigation order.
- Component tests cover ARIA metadata, roving focus, Arrow/Home/End navigation, branch disclosure,
  Enter/Space activation, evidence outside the tree, stale request rejection, request failure,
  related-post opening, and unresolved relations.
- Storybook includes ordinary and malformed-relation states.
- Focused ontology/frontend tests, frontend lint, complete Vitest suite, production build, and
  Storybook build must pass on the exact PR head.

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

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

An entity that is authorized for the caller must not disappear because a hierarchy edge is malformed.
At the same time, the browser must not invent a different parent or promote an inferred relation to an
authoritative ontology fact.

The W3C Organization Ontology models hierarchical containment through `org:subOrganizationOf` and
allows formal organizations to contain other formal organizations. The WAI-ARIA Authoring Practices
Tree View Pattern defines `tree`, `treeitem`, `group`, branch `aria-expanded`, roving focus, and arrow-key
navigation for an interactive hierarchy.

## Decision

1. Move customer hierarchy assembly into `frontend/src/customerMasterTree.ts`.
2. Preserve API order for roots and siblings.
3. Preserve every unique authorized entity.
4. Keep a valid parent link only when the parent is present in the authorized response.
5. Promote a missing-parent, self-parent, or every member of a detected cycle to a visible root and
   mark the relation `unresolved`; do not infer a replacement parent.
6. Render the projection through the reusable `CustomerMasterTree` component.
7. Separate hierarchy disclosure from evidence disclosure:
   - Left/Right Arrow collapses, expands, and moves to parent or first child.
   - Up/Down Arrow, Home, and End move through visible tree items.
   - Activating a tree item opens source-backed related posts without changing the hierarchy branch.
8. Explicitly declare `aria-level`, `aria-posinset`, and `aria-setsize` so assistive technology does not
   depend on browser inference.
9. Keep the current flat API as a bounded authorized projection. A future temporal, multi-context
   hierarchy model remains a separate backend/ontology change.

## Consequences

### Positive

- Ordinary Group → Company → Plant structures remain hierarchical.
- Malformed relations are visible and reviewable instead of silently omitted.
- Keyboard and screen-reader users receive a real tree interaction model.
- The component is independently testable and available in Storybook.
- Related-post evidence remains source-backed and lazy-loaded.

### Trade-offs

- A malformed relation is displayed as an unresolved root, which is intentionally less specific than
  guessing a parent.
- The projection still represents one `parent_entity_id` context. Legal ownership, operating
  structure, sales roll-up, billing structure, and time-valid hierarchy require a normalized,
  effective-dated relation model in a later ADR.
- The referenced Figma file does not contain a dedicated public customer-tree frame. This change uses
  the existing design-token and Storybook boundary rather than claiming pixel equivalence to a
  nonexistent frame.

## Verification

- Pure tests cover a three-level hierarchy, missing parent, self-parent, multi-node cycle, descendant
  preservation, ordering, and collapsed navigation order.
- Component tests cover ARIA levels, roving focus, Arrow navigation, evidence loading, stale request
  rejection, related-post opening, and unresolved relations.
- Storybook includes ordinary and malformed-relation states.
- Frontend lint, complete Vitest suite, production build, and Storybook build must pass on the exact
  PR head.

## References — APA 7th

World Wide Web Consortium. (2014). *The Organization Ontology*.
https://www.w3.org/TR/vocab-org/

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*.
https://www.w3.org/TR/WCAG22/

World Wide Web Consortium, Web Accessibility Initiative. (n.d.). *Tree view pattern*.
https://www.w3.org/WAI/ARIA/apg/patterns/treeview/

# ADR 0129: Customer-centered three-pane Customer Master workspace

- **Status:** Accepted
- **Date:** 2026-08-21
- **Owners:** Customer Master product surface and evidence navigation
- **Figma file ID:** `SBpgot7uTvMxEaxUwvoc0S`
- **Figma desktop frame:** `313:2`
- **Figma mobile frame:** `314:2`

## Context

ADR 0124 established a cycle-safe, authorized WAI-ARIA tree for Group → Company → Plant
containment and deliberately kept related-post evidence outside the tree ownership boundary. That
corrected malformed hierarchy handling and keyboard navigation, but the product composition remained
vertically fragmented:

1. the hierarchy occupied the first block;
2. selecting an entity caused evidence to appear below the complete tree;
3. relationship-network, unresolved-hint, source-author, and Keyman blocks continued further down;
4. the currently selected customer was not held as the stable visual center of the task.

Users therefore had to remember which entity they selected while scanning a long page. Parent/child
relationships and source evidence were available, but they were not arranged around the customer that
the user was trying to understand. A free-form graph would add visual complexity and would also risk
presenting inferred edges as if they were authoritative Customer Master facts.

The uploaded *웹 시스템 UI·UX 표준 가이드 Ver.3.0* requires clear navigation hierarchy and active
state, a 1024 px PC boundary, a 768 px phone boundary, responsive content ordering, system-font
control, and content-page actions that remain discoverable on small screens. ADR 0118 adopted those
breakpoints and design-token rules for LineageWeave.

## Decision

1. Compose Customer Master as one customer-centered workspace with three explicit semantic panes:
   - **01 Customer hierarchy:** the existing authorized, cycle-safe WAI-ARIA tree;
   - **02 Selected customer:** one stable customer summary with the visible parent and direct child
     relationships around that customer;
   - **03 Linked evidence:** only source-backed related posts, with the existing open-post handoff to
     Event Lineage.
2. Keep the selected customer separate from whether its evidence pane is open. Closing evidence must
   not lose the customer's centered relationship context.
3. Keep `corporate_entity.parent_entity_id` authoritative. The middle pane may recenter on a visible
   parent or direct child, but it must not infer hidden parents, siblings, ownership, or alternative
   organizational edges.
4. Preserve all ADR 0124 hierarchy semantics and keyboard behavior. Branch disclosure remains
   independent from customer selection.
5. Keep source-backed related posts outside `role="tree"`. A tree item may reference the evidence
   region with `aria-controls` only while that region exists.
6. Preserve stale-request rejection and per-entity evidence caching when users move rapidly between
   customers.
7. Use existing design tokens for border, focus, color, status, spacing, and dark-mode behavior. Do
   not introduce a second Customer Master palette.
8. Use the UI·UX guide's three responsive tiers:
   - **PC, greater than 1024 px:** all three panes in one horizontal row;
   - **Tablet, up to 1024 px:** hierarchy and selected customer side by side, evidence full width;
   - **Phone, up to 768 px:** hierarchy → selected customer → evidence as one vertical task sequence.
9. Maintain complete product copy for all five supported locales: English, Korean, Chinese,
   Japanese, and Vietnamese.
10. Represent the desktop, phone, malformed-relation, and unselected states in Storybook. The Figma
    frames are the visual design evidence; Storybook remains the executable state inventory.

## Alternatives considered

### Keep the vertical tree and accordion evidence

Rejected because it preserves the long-memory task: the selected customer scrolls away while evidence
and other relationship blocks appear below.

### Replace the tree with a network graph

Rejected because graph layout does not provide a predictable hierarchy scan, is harder to operate with
a keyboard, and can blur the boundary between authoritative containment and inferred relationships.
Graphs remain appropriate for Event Lineage, not for the Customer Master authority projection.

### Put all relationships in one wide table

Rejected because a table flattens the Group → Company → Plant path and makes recentering around one
customer less direct. Exact-value tables may supplement a graph, but they do not replace the
hierarchical navigation contract here.

## Consequences

### Positive

- The selected customer remains visually and semantically central while users inspect its parent,
  children, and evidence.
- The page expresses a stable left-to-right task: choose → understand relations → verify evidence.
- Evidence can close without losing the selected customer or its relationship context.
- Existing WAI-ARIA tree behavior, malformed-relation visibility, authorization scope, and
  source-backed evidence boundaries remain intact.
- Responsive layouts preserve the same semantic order instead of hiding relationship context behind a
  separate phone-only interaction model.
- Figma and Storybook now describe the same product surface and edge states.

### Trade-offs

- A three-pane desktop layout uses more horizontal space than the previous vertical list.
- Tablet users receive a two-row composition rather than all three panes in one row.
- Only the authoritative parent and direct children are shown in the middle pane. Siblings, historical
  roles, billing structure, and inferred relationships require separately typed products or later
  effective-dated relation models.

## Verification

- Existing `CustomerMasterTree` tests continue to cover WAI-ARIA metadata, roving focus,
  Arrow/Home/End navigation, independent branch disclosure, stale request rejection, request failure,
  evidence caching, and malformed hierarchy members.
- New workspace tests cover the three-pane composition, stable selected-customer state, parent and
  direct-child recentering, source evidence outside the tree, evidence close/reopen behavior,
  unresolved relation explanation, leaf boundary copy, and five-locale copy completeness.
- Frontend lint, TypeScript, complete Vitest, production build, and Storybook build must pass on the
  exact PR head.
- GitHub protected checks and independent review remain the final merge authority.

## References — APA 7th

ContextualWisdomLab. (2026). *ADR 0118: UI·UX Standard Guide Ver.3.0 design overhaul*.

ContextualWisdomLab. (2026). *ADR 0124: Cycle-safe customer master tree projection*.

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*.
https://www.w3.org/TR/WCAG22/

World Wide Web Consortium, Web Accessibility Initiative. (n.d.). *Tree view pattern*.
https://www.w3.org/WAI/ARIA/apg/patterns/treeview/

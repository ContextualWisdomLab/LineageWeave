# ADR 0365: Customer Master malformed hierarchy presentation

- Status: Accepted
- Date: 2026-09-05

## Context

An authorized Customer Master response can contain an entity whose parent is not
visible, points to itself, or participates in a cycle. Dropping that entity hides
authorized customer evidence. Treating the malformed edge as valid can recurse
forever or exhaust the browser call stack. Changing the stored parent would invent
organizational authority.

## Decision

The presentation projection keeps every uniquely identified authorized entity. It
omits a missing, self-referential, or one deterministic cycle-closing parent edge and
promotes that entity to a visible root. A presentation-only issue code travels to the
render boundary, where localized customer copy discloses the omitted edge. It does not
change the API's authoritative name, level, identifier, or stored parent.

Duplicate, blank, and whitespace-aliased canonical entity identifiers fail closed.
Tree construction, flattening, and rendering are iterative so valid depth cannot
exhaust the JavaScript call stack. Sibling and cycle-break ordering uses code-point
comparison and carries no ranking or organizational inference.

## Consequences

- Authorized entities stay visible even when their visible hierarchy is incomplete.
- The screen distinguishes source facts from a presentation-only omitted-edge notice.
- A malformed identity yields the existing load failure instead of an ambiguous tree.
- Deep hierarchies render as one flat DOM list with visual indentation.

## Alternatives considered

- Drop malformed descendants: rejected because it hides authorized evidence.
- Reassign a replacement parent: rejected because the product has no authority to
  invent organizational structure.
- Render the source graph recursively: rejected because cycles and valid deep inputs
  can prevent the screen from rendering.

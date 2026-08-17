# ADR-0014: Related-node chips share one module and story inventory

- Status: Accepted
- Date: 2026-08-17
- Stack: `feat/related-node-person-side-labels-main` (#92) @ `9bb5829`

## Context

Related-node walk chips live inline in `App.tsx`. The Figma synthetic
chip library (ADR 0002,
https://www.figma.com/design/nMmCeOdwGMKPxDrG8pWEAX) names the same
four buyer states: unique affiliation, side-only when two orgs would
invent a primary, organization level, and post title only. Repeating
the caption and accessible-name rules in App, tests, and a later
Storybook host would drift.

## Decision

1. `relatedNodeCaption` / `relatedNodeChipAccessibleName` own the
   caption contract. Person chips name side plus a unique org.
   Multiple distinct affiliations stay omitted. Organization chips
   use the entity-level label. Post chips are the title only.
2. `RelatedNodeChip` is the only repeating walk control.
3. `RelatedNodeChip.stories.tsx` is the inventory. Host it with
   Storybook 10 when the later token stack lands. Until then the
   same states are locked by vitest.

This slice does not add `affiliation_ambiguous` or a "multiple
organizations" caption. That next-action copy is #123 / #192.

## Consequences

Walking from Demo Corp still shows `Ada West, Demo Corp (Our side)`.
Priya Nair stays `Priya Nair (Counterparty)`. Click a chip to continue
the walk or open the post. Do not mix this increment into #74.

## References

World Wide Web Consortium. (2024). *Web content accessibility
guidelines (WCAG) 2.2* (Success Criterion 2.5.3 Label in Name).
https://www.w3.org/TR/WCAG22/#label-in-name

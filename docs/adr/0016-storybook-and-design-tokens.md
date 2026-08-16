# ADR-0016: Storybook inventory and design tokens for repeating walk chips

- Status: Accepted
- Date: 2026-08-16

## Context

Related-node chips are the buyer's next-click control after a Keyman
walk starts. ADR-0014 locked the caption contract (unique org, plural
set, missing affiliation, organization level, post title). ADR-0015
records the later affiliation-interval follow-up and must keep that
number. Those chips were still inlined in `App.tsx` with one-off CSS,
so a designer or buyer could not inspect the three affiliation states
without seeding the full stack. The same colors and radii were
repeated as hex literals.

Figma remains the design-reference boundary in ADR 0002: this public
repository must not ingest the source organization's confidential
frames. Storybook is the inspectable inventory that can live here.

## Decision

- Repeating walk objects are modules (`RelatedNodeChip`) whose captions
  come from `relatedNodeCaption`.
- Visual states are stories under `frontend/src/*.stories.tsx`. Run
  `pnpm run storybook` in `frontend/` to compare unique, plural, and
  missing affiliation chips side by side. Click a person or
  organization story to rehearse the walk; click a post story to
  rehearse opening the source.
- Color, space, and radius tokens live in
  `frontend/src/tokens/design-tokens.json` using the Design Tokens
  Community Group format (Design Tokens Community Group, 2025). CSS
  custom properties in `tokens.css` are the runtime aliases. Token
  paths are two or more segments (`color.text`, `space.chip-gap`).
- `pnpm run build-storybook` is a required frontend CI step so a
  broken story fails the same way a broken caption test does.

## Consequences

A buyer can open Storybook and see `Priya Nair, multiple organizations
(Counterparty)` next to `Priya Nair (Counterparty)` without guessing
which chip to click after `make seed`. Token changes land in one
catalog. Figma stays optional and still must not import real-org
frames.

## References

Design Tokens Community Group. (2025). *Design tokens format module*
(W3C Community Group Draft Report).
https://www.w3.org/community/design-tokens/

Storybook. (2026). *Storybook for React with Vite* (Version 10.5).
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2023). *Web Content Accessibility
Guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/

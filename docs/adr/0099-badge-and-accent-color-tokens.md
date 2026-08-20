# ADR 0099 — Badge and accent colors are design tokens, not inline hex

**Decision status:** Accepted
**Date:** 2026-08-20
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Figma File URL:** https://www.figma.com/design/1Su3lDRmiZdcUs47t1QwIX

## Context

`frontend/src/App.css` had accumulated roughly a dozen repeated inline hex
colors for the same handful of semantic surfaces: the lineage-link accent
pair (direct/indirect), the "current" selection outline, the R&R actor-type
badges (person/organization/team), and the relation-verification status
badges (pending/corroborated/uncorroborated). None of them had a dark-mode
counterpart, so `@media (prefers-color-scheme: dark)` left every pastel
badge exactly as light as it is in light mode -- a buyer using dark mode
would see bright person/org/team chips clashing against the dark chrome
defined in `frontend/src/styles/tokens.css`.

`styles/tokens.css` already establishes the project's token convention
(`--color-accent`, `--color-accent-background`, `--color-accent-border`,
each with a `prefers-color-scheme: dark` override) per ADR 0002's design-
system boundary (Figma File ID above): that file is the safe, org-content-
free surface for future token and component work.

## Decision

Extend `styles/tokens.css` with the missing semantic pairs, following the
existing naming and override pattern exactly:

- `--color-border-subtle`, `--color-accent-info`,
  `--color-accent-info-background`, `--color-accent-secondary`,
  `--color-accent-secondary-background`
- `--badge-actor-person-{bg,text}`, `--badge-actor-organization-{bg,text}`,
  `--badge-actor-team-{bg,text}`
- `--badge-status-pending-{bg,text}`, `--badge-status-success-{bg,text}`,
  `--badge-status-danger-{bg,text}`

Every one gets a `prefers-color-scheme: dark` override (desaturated/alpha
background, lightened text) rather than being left to just inherit the
light value. `App.css` now references these custom properties instead of
inline hex at every one of the ~13 sites that previously repeated the same
literal color.

## Rationale

- Repeated literal colors across a stylesheet are the same defect class as
  a repeated magic number in code: the next person to retheme (or the next
  dark-mode bug report) has to grep for six-digit hex strings instead of
  reading one token block.
- A badge with no dark-mode pair is not neutral -- it actively regresses
  the buyer's dark-mode experience, which is the concrete "product gap a
  buyer would notice" this token pass closes.
- Reusing ADR 0002's already-cleared Figma file (rather than opening a new
  one) keeps the design-system boundary singular and avoids re-litigating
  the confidentiality review that file already passed.

## Consequences

- Future badge/status colors should extend this same token block, not add
  another inline hex literal to `App.css`.
- The Figma file at the ID above is the reference surface if these tokens
  are ever pushed into a Figma design-system sync; no organization-
  identifying content has been added to it by this change.
- `frontend/src/App.css` and `frontend/src/styles/tokens.css` were verified
  with `tsc -b`, `vitest run` (125 passing), and a production `vite build`
  before this ADR was written.

## Related

Builds on [ADR 0002](0002-figma-access-boundary.md)'s Figma boundary and
the token pattern `styles/tokens.css` already established for
`--color-accent`.

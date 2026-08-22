# ADR 0122: Ask citations open a focused evidence Layer Popup

- Status: Accepted
- Date: 2026-08-22
- Related: [0121](0121-ask-image-citation.md), [0120](0120-ask-multi-lineage-graph.md)

## Context

Reading one Ask citation's evidence meant either scanning the inline fact
list rendered under every citation at once, or leaving the answer
entirely to open the full post detail popup (`PostDetailPopup`) -- there
was no focused way to inspect a single citation's evidence without either
losing the answer or wading through unrelated citations' facts on screen
at the same time.

## Decision

`AskEvidenceLayerPopup` (`frontend/src/components/`) is a new, focused
modal opened by a "View evidence" button on each citation. It shows only
that one cited post's text evidence facts (ADR 0047's evidence chips) and
image evidence (ADR 0121) without navigating away from the answer or
displaying any other citation's evidence. It reuses the app's existing
`.popup-backdrop`/`.popup-panel` visual language (`PostDetailPopup`'s own
classes) rather than introducing a new modal style.

Its dialog semantics are stricter than `PostDetailPopup`'s: `role="dialog"`,
`aria-modal="true"`, `aria-labelledby` naming the cited post's title,
Escape-to-close, backdrop-click-to-close, and initial focus moved onto the
panel on mount. `PostDetailPopup` has none of these today; this decision
does not retrofit them there -- a focused follow-up, not silently expanded
scope of this change.

`chatEvidenceKindLabel` (previously a private `App.tsx` helper) moved to
`frontend/src/evidenceKindLabels.ts` so both `App.tsx` and the new
component read from one label map instead of maintaining two copies that
could drift.

## Considered alternatives

- Extend `PostDetailPopup` itself with an "evidence-only" display mode:
  rejected -- that component already fetches and renders a large surface
  (summary, 5W1H, Keymen, counterparties, Event Lineage, evaluation); a
  mode flag threading through all of that to suppress everything except
  evidence is a larger, riskier change than a small, independent
  component with its own narrow props.
- Reuse the post-scoped chat's existing `EvidencePanel` (a non-modal,
  `role="complementary"` sliding panel that shows a cited post's full
  body): rejected -- it fetches and renders the entire post body, not
  scoped facts/images, and its non-modal layout assumes the post-scoped
  chat's own screen real estate, which Global Ask's answer view does not
  have.

## Consequences

- A reader can inspect one citation's evidence in a focused layer without
  losing their place in the answer.
- The Layer Popup pattern (a small, dialog-semantic overlay scoped to one
  piece of evidence) is now precedent for future evidence surfaces that
  don't warrant a full post detail popup.
- `PostDetailPopup`'s missing dialog semantics (no `role="dialog"`, no
  Escape-to-close) remain an open accessibility gap, tracked here as a
  known follow-up rather than fixed by this decision.

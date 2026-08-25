# ADR 0153: Ask citations open a focused evidence Layer Popup

- Status: Accepted
- Date: 2026-08-22
- Related: [0152](0152-ask-image-citation.md), [0151](0151-ask-multi-lineage-graph.md)

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
image evidence (ADR 0152) without navigating away from the answer or
displaying any other citation's evidence. It reuses the app's existing
`.popup-backdrop`/`.popup-panel` visual language (`PostDetailPopup`'s own
classes) rather than introducing a new modal style.

Both evidence and post-detail layers use `role="dialog"`, `aria-modal="true"`,
an accessible title, Escape-to-close, backdrop-click-to-close, focus
containment, and opener focus restoration. Post-detail navigation moves focus
back to the same dialog for the newly selected post. Native DOM visibility
and disclosure state exclude collapsed, hidden, inert, and CSS-invisible
controls from both focus orders.

Each evidence row separates its type, value, OCR text, and image tags with
visible punctuation. Adjacent spans must not collapse into ambiguous text.

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
- The follow-up now applies the same dialog semantics, Escape-to-close,
  initial focus, focus restoration, focus containment, and selected-post
  navigation refocus to `PostDetailPopup`. Collapsed, hidden, inert, and
  CSS-invisible descendants are excluded from its focus order; both popup
  variants retain their separate content and data-fetching boundaries.

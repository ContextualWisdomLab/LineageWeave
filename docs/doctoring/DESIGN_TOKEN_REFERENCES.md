# Design-token and Storybook traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** `frontend/src/styles/tokens.css`, repeated chip/close modules, the
Ask evidence dialog, and the Storybook inventory.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C Design Tokens Format Module 2025.10 | Name color, space, type, and radius once; consume those names from repeated objects. | `frontend/src/styles/tokens.css` defines `--color-*`, `--space-*`, `--size-control-min`, `--radius-chip`, `--radius-control`, `--radius-panel`, and `--font-*`. `CitationChip`, `PopupCloseButton`, `CutoffKnownBody`, and `LineageEntityPicker` read those names through `App.css`. |
| Storybook for React & Vite | Catalog repeated controls so a buyer can try the next click without reading `App.tsx`. | `frontend/src/components/*.stories.tsx` and `docs/storybook-inventory.md`. |
| WCAG 2.2 | Give interactive controls programmatic names, meet SC 2.5.8's 24×24 CSS-pixel minimum target, and announce an asynchronous evidence failure instead of leaving a perpetual loading state. | Component interaction tests exercise the named controls; Dashboard evidence links consume `--size-control-min`; `EvidencePanel` exposes its terminal failure with `role="alert"`. This is targeted evidence, not a claim of complete WCAG conformance. |
| WAI-ARIA APG Dialog (Modal) Pattern | A surface marked `aria-modal="true"` must behave modally: focus moves inside, `Tab` and `Shift+Tab` remain inside, and `Escape` closes the layer. | `AskEvidenceLayerPopup` moves initial focus inside the dialog and explicitly cycles forward/backward keyboard focus between its actionable controls; component tests cover both focus-loop directions and Escape. Its evidence lists use dialog-specific accessible labels so assistive technology can distinguish the modal list from the still-rendered inline answer. |

## APA 7th references

Design Tokens Community Group. (2025). *Design Tokens Format Module 2025.10*
(W3C Community Group Final Specification).
https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (n.d.). *Dialog (modal) pattern*. WAI-ARIA
Authoring Practices Guide. Retrieved August 22, 2026, from
https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

# Design-token and Storybook traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** `frontend/src/styles/tokens.css`, repeated chip/close modules, and
the Storybook inventory.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C Design Tokens Format Module 2025.10 | Name color, space, type, and radius once; consume those names from repeated objects. | `frontend/src/styles/tokens.css` defines `--color-*`, `--space-*`, `--size-control-min`, `--radius-chip`, `--radius-control`, `--radius-panel`, and `--font-*`. `CitationChip`, `PopupCloseButton`, `CutoffKnownBody`, and `LineageEntityPicker` read those names through `App.css`. |
| Storybook for React & Vite | Catalog repeated controls so a reader can try the next click without reading `App.tsx`. | `frontend/src/components/*.stories.tsx` and `docs/storybook-inventory.md`. |
| WCAG 2.2 | Give interactive controls programmatic names and announce an asynchronous evidence failure instead of leaving a perpetual loading state. | Component interaction tests exercise the named controls; `EvidencePanel` exposes its terminal failure with `role="alert"`. This is targeted evidence, not a claim of complete WCAG conformance. |

## APA 7th references

Design Tokens Community Group. (2025). *Design Tokens Format Module 2025.10*
(W3C Community Group Final Specification).
https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

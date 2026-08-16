# Design-token and Storybook traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** `frontend/src/styles/tokens.css`, repeated chip/close modules, and
the Storybook inventory.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C Design Tokens Format Module 1.0 | Name color, space, type, and radius once; consume those names from repeated objects. | `frontend/src/styles/tokens.css` defines `--color-*`, `--space-*`, `--radius-chip`, and `--font-*`. `CitationChip`, `PopupCloseButton`, and `StatusAlert` read those names through `App.css`. |
| Storybook for React & Vite | Catalog repeated controls so a buyer can try the next click without reading `App.tsx`. | `frontend/src/components/*.stories.tsx` and `docs/storybook-inventory.md`. |
| WCAG 2.2 SC 4.1.3 Status Messages | Announce a fail-closed status without moving focus, so the operator hears the next action. | `StatusAlert` uses `role="alert"` and `--color-status-alert`. |

## APA 7th references

Design Tokens Community Group. (2025). *Design Tokens Format Module 1.0*
(W3C Community Group Draft Report). https://tr.designtokens.org/format/

Kirkpatrick, A., Campbell, A., Cooper, M., & Adams, C. (Eds.). (2023).
*Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation).
World Wide Web Consortium. https://www.w3.org/TR/WCAG22/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

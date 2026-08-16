# Design-token and Storybook traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** `frontend/src/styles/tokens.css`, repeated chip/close modules, and
the Storybook inventory.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C Design Tokens Format Module 1.0 | Name color, space, type, and radius once; consume those names from repeated objects. | `frontend/src/styles/tokens.css` defines `--color-*`, `--space-*`, `--radius-chip`, and `--font-*`. `CitationChip`, `PopupCloseButton`, `AnalysisRunRequestButton`, and `AnalysisRunListButton` read those names through `App.css`. |
| Storybook for React & Vite | Catalog repeated controls so a buyer can try the next click without reading `App.tsx`. | `frontend/src/components/*.stories.tsx` and `docs/storybook-inventory.md`. |
| WCAG 2.1 | Name the next action on the control the buyer activates. | Request and list buttons expose AccNames (`Request a lineage reconstruction`, `Open analysis run: …`). |

## APA 7th references

Design Tokens Community Group. (2025). *Design Tokens Format Module 1.0*
(W3C Community Group Draft Report). https://tr.designtokens.org/format/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2018). *Web Content Accessibility Guidelines
(WCAG) 2.1* (W3C Recommendation). https://www.w3.org/TR/WCAG21/

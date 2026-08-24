# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
buyer-facing control you can click before changing product CSS.

| Story | Buyer next action | Token / module |
|---|---|---|
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `Evidence/PostBody` | Open Image regions and read each bounding range beside its caption; inspect the whitespace-caption state to confirm the image keeps a usable fallback name. | `--text-muted`, `PostBody` |
| `Evidence/AskEvidenceLayerPopup` | Inspect one citation without leaving the answer; close to continue the answer or open the complete source post. Stories cover text/image evidence, no-evidence, missing OCR, null caption, and blank-caption fallback states. | shared popup tokens through `App.css`, `PopupCloseButton`, `AskEvidenceLayerPopup` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Admin/AdminPanel` | Change the tenant brand name, then verify the saved or failed state before leaving settings. | `--surface`, `--border`, `--space-panel-block`, `AdminPanel` |
| `Lineage/LineageDag` | Read Before on the A-100 fork, then click the revised-quote row to open that post; compare empty, single-branch, grouped/forked, mobile-scroll, ungrouped, and long-title states before changing graph CSS. On narrow viewports, swipe the named viewport or focus it and use arrow keys to inspect the full lineage. | `--color-accent-background`, `--radius-control`, `--surface`, `--border`, `--color-focus-border`, `--size-control-min`, `LineageDag` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `Evidence/OntologyExplorer` | Inspect typed people/orgs/posts, then open authorized evidence. Distinct from Event Lineage. | `--color-primary`, `--color-table-border`, `OntologyExplorer` |
| `Reports/LeftoverPairList` | Read residual R, observed Y, expected E, map rank, and distance after IRT main effects, then open the named post. | `--color-chip-border`, `LeftoverPairList` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 2025.10*
(W3C Community Group Final Specification).
https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

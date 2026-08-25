# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
buyer-facing control you can click before changing product CSS.

| Story | Buyer next action | Token / module |
|---|---|---|
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `Evidence/OrganizationAliasChip` | Click a cataloged org; the parenthetical is the unique corroborated SKOS companion. | `--color-chip-border`, `--radius-chip`, `OrganizationAliasChip` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `Navigation/WorkspaceNav` | Open 게시판, 고객 마스터, 달력, or Ask Agent. Admin is not a GNB tab. | `--gnb-height`, `--gnb-active-indicator-color`, `WorkspaceNav` |
| `Evidence/OntologyExplorer` | Inspect typed people/orgs/posts, then open authorized evidence. Distinct from Event Lineage. | `--color-primary`, `--color-table-border`, `OntologyExplorer` |
| `Reports/LeftoverPairList` | Read residual R, observed Y, expected E, map rank, and distance after IRT main effects, then open the named post. | `--color-chip-border`, `LeftoverPairList` |
| `Reports/LeftoverInteractionMap` | Read leftover-map post and criterion positions after IRT main effects, then open the named leftover-pair post. | leftover-map tokens, `LeftoverInteractionMap` |

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

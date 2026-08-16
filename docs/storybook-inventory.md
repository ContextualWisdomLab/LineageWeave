# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
buyer-facing control you can click before changing product CSS.

| Story | Buyer next action | Token / module |
|---|---|---|
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `AnalysisRuns/RequestButton` | Click to record a Pending lineage cutoff bag. | `--space-home-header-gap`, `AnalysisRunRequestButton` |
| `AnalysisRuns/ListButton` | Open the named run and confirm its cutoff posts. | `--space-list-item-block`, `--space-list-item-gap`, `AnalysisRunListButton` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 1.0*
(W3C Community Group Draft Report). https://tr.designtokens.org/format/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

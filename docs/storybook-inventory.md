# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
buyer-facing control you can click before changing product CSS.

| Story | Buyer next action | Token / module |
|---|---|---|
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 1.0*
(W3C Community Group Draft Report). https://tr.designtokens.org/format/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

## Project lifecycle history

`Buyer/Project history timeline` covers the complete lifecycle, no-assignment,
single-assignment, hidden-evidence-removed, truncated, and empty-evidence
states. The stories use synthetic data and preserve the same source-opening,
non-causal relation, responsive, and handover-gap contracts as the production
component (ADR 0100; Figma `SBpgot7uTvMxEaxUwvoc0S`, node `308:2`).

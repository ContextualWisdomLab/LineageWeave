# ADR 0296 — Grouping comparison explained-leftover share

**Decision status:** Proposed

## Problem
The serialized comparison surface omits persisted explained-leftover share `e = R̂²/R²`. The historical implementation rendered a descendant badge inside a button with an explicit accessible name, so the visible metric was not reliably announced as part of the action.

## Decision
Format only persisted `leftover_map_explained_share` through `formatLeftoverMapExplainedShare`. Append the localized label and formatted value to the pair button accessible name, and mark the duplicate visible badge `aria-hidden`. Missing/non-finite values omit only this suffix; finite zero and values above 1 remain explicit. Never derive or clamp `e` from `R̂`, `R`, distance, coordinates, residuals, rank, coverage, or visible-subset proxies. fast-mlsirm remains psychometric owner.

This ADR remains Proposed while Draft. Acceptance requires current-head hosted tests, rendered keyboard/screen-reader/a11y evidence, canonical eight-locale ledger convergence, independent approval, and normal protected-branch merge.

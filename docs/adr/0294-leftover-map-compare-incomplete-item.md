# ADR 0294 — Grouping comparison incomplete-item coverage

**Decision status:** Proposed

## Problem
The grouping comparison strip omits the persisted incomplete-item count even though the full persisted grouping read model already carries authorization-filtered coverage.

## Decision
Render `leftoverMapIncompleteItemCount(row.leftover_map_coverage)` with the distinct accessible label `Leftover map comparison incomplete items`. Reuse the persisted-count validator. Do not derive the count from scored-minus-used, pair count, plotted criteria, or any other client-side proxy.

Only a full persisted grouping authorized by the API may carry the coverage object. Partial visibility must keep coverage absent; the frontend must not reconstruct a hidden full-population denominator or recompute psychometrics from the visible subset. Valid persisted zero remains visible. Missing, negative, non-integer, or contradictory counts fail closed.

This ADR remains Proposed while the PR is Draft. Accepted status requires current-head hosted tests, rendered keyboard/accessibility evidence, canonical eight-locale translation-ledger convergence, independent approval, and normal protected-branch merge.

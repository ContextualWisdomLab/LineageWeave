# ADR 0027 — Focus the leftover evaluation row on the opened post

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0026 names leftover pair context on the opened post and marks the
matching evaluation row. The status still says “Read that evaluation
row next,” but the row stayed wherever it sat in the list. A long
rubric buries the leftover criterion under the fold.

## Decision

When leftover pairs for the open post match an evaluation row, that
row is the current evaluation item and receives focus.

1. A leftover-matching row sets `aria-current="true"` and the
   leftover badge from ADR 0026.
2. The first leftover pair in the loaded report payload is the
   focus target. When the host provides layout,
   `scrollIntoView({ block: "nearest" })` runs; keyboard
   `tabIndex={-1}` focus always runs. Later leftover rows stay
   marked, not invented.
3. A post with no leftover pair, or a row whose criterion does not
   match, is not current and is not focused.

Do not invent leftover numbers. Do not persist a second leftover
store. Do not mix this into #74 or #92.

## Consequences

After `make seed`, opening the closest leftover pair moves keyboard
focus to the sales-lead evaluation row. Mean θ stays on the report
panel. Rankings stay on ADR 0024. TEPP stays on #214.

## Related

Depends on [ADR 0026](0026-leftover-pair-open-context.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

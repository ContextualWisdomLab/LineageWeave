# ADR 0294 — Name leftover-map incomplete item coverage on the grouping comparison strip

**Decision status:** Proposed
**Date:** 2026-09-07

## Context
`report_leftover_map_coverage.incomplete_item_count` is an existing persisted measurement fact. The serialized successor needs a distinct grouping-comparison presentation without reusing historical ADR 0292/v2.49.0.

## Decision
Caption persisted incomplete-item count through `leftoverMapIncompleteItemCount(row.leftover_map_coverage)` and the distinct accessible name `Leftover map comparison incomplete items`. This aggregate is available only for a caller who can see the full persisted grouping population. Partial visibility omits `row.leftover_map_coverage`; never recompute psychometric coverage or dropped-item count from the visible subset. Missing, invalid, or inconsistent values omit the note; persisted zero remains visible. No SQL, schema, theta, leftover score, or alternate measurement authority is added.

## Alternatives rejected
Client-side scored-minus-used derivation and direct table reads are rejected because they create a second measurement or authorization authority. Reusing pair-list or graphic labels is rejected because those are distinct surfaces.

## Consequences
Fully visible comparisons name persisted dropped criteria; partial visibility fails closed. ADR 0294 remains Proposed while this PR is Draft and may become Accepted only through normal protected-branch merge/release evidence.

## References
Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403. https://doi.org/10.1007/s11336-021-09762-5

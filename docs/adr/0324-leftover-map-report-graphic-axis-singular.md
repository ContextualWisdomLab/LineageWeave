# ADR 0324 — Name persisted singular values on report leftover-map graphic axes

**Decision status:** Proposed
**Date:** 2026-08-31

## Context

LineageWeave persists leftover-map axis share and Gabriel singular value `σ_k`. Comparison graphics and comparison-strip evidence can already expose persisted `σ_k`; the report graphic still shows share only. That hides scale evidence on the report graphic and creates inconsistent semantics for the same persisted axes.

Missingness is independent. A valid finite, non-negative `σ_k`, including `0`, must remain visible when share is absent; valid share must remain visible when `σ_k` is absent or invalid. Neither value is reconstructed from the other.

## Decision

Report graphic axes use distinct copy:

- singular only: `leftover-map axis {axis} σ {value}`;
- singular plus share: `leftover-map axis {axis} σ {value} ({share}%)`;
- share only: the existing `leftover-map axis {axis} ({share}%)`;
- neither usable: the existing axis name without invented evidence.

No square root, normalization, SQL, migration, or owner duplication is introduced. The rendering consumes LineageWeave-owned persisted evidence and leaves comparison copy distinct.

## Consequences

Report and comparison graphics now preserve the same evidence semantics while keeping surface-specific labels. This ADR remains **Proposed** until fresh exact-head frontend, browser/accessibility, security, and independent-review evidence is current.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403. https://doi.org/10.1007/s11336-021-09762-5

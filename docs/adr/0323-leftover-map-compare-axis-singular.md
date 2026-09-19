# ADR 0323 — Name persisted singular values on grouping comparison leftover-axis badges

**Decision status:** Proposed
**Date:** 2026-08-31

Amends leftover-map axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)) and the grouping comparison strip ([ADR 0149](0149-period-grouping-comparison.md)). It follows comparison-graphic singular evidence ([ADR 0321](0321-leftover-map-compare-plot-singular.md)) and report-axis singular badges ([ADR 0322](0322-leftover-map-axis-singular.md)) without changing either contract.

## Context

LineageWeave already persists leftover-map axis share and singular value `σ_k` for each axis. The report surface and the grouping-comparison graphic can expose that evidence, but the grouping comparison strip still omits it. Buyers therefore cannot read the persisted axis scale from the comparison strip itself.

The two measurements have different missingness. A valid share must remain visible when `σ_k` is absent or invalid; a valid finite, non-negative `σ_k` — including `0` — must remain visible when share is absent or invalid. Neither value may be reconstructed from the other. This increment does not add persistence, SQL, psychometric estimation, or a new canonical owner.

## Decision

For comparison-strip leftover axes, project already persisted values into four independent states:

- combined: `leftover map comparison leftover axis {axis} σ {value} {share}%`;
- singular only: `leftover map comparison leftover axis {axis} σ {value}`;
- share only: `leftover map comparison leftover axis {axis} {share}%`;
- neither usable: omit the badge.

`σ_k` is accepted only when finite and non-negative; `σ=0` remains explicit. Share is accepted only when finite. No `Math.sqrt`, inversion, normalization, or other derivation is allowed. The copy remains distinct from report-axis badges and from comparison-graphic axis captions.

The comparison rendering reuses LineageWeave-owned persisted evidence and existing localization composition. It does not copy logic from fast-mlsirm, TEPP, or any other canonical owner.

## Consequences

The grouping comparison buyer path exposes axis evidence without conflating scale and share. Missing evidence fails closed by omission, while usable evidence survives independently. Existing comparison-graphic interaction, pointer/keyboard behavior, and post navigation remain unchanged.

This ADR stays **Proposed** until the exact-head implementation, executable contract, frontend tests, accessibility/browser evidence, and independent review are current.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403. https://doi.org/10.1007/s11336-021-09762-5

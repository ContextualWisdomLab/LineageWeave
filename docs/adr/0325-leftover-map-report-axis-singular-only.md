# ADR 0325 — Preserve singular-only and share-only report-axis evidence

**Decision status:** Proposed
**Date:** 2026-08-31

## Context

LineageWeave persists two different measurements for a leftover-map axis: Gabriel singular value `σ_k` and axis share. They have independent missingness. The report badge path previously chose its rendering branch from `σ_k` alone and formatted a missing share through numeric arithmetic, which can surface `NaN%` and erase the distinction between unavailable evidence and a measured value.

A finite, non-negative persisted `σ_k`, including `0`, must remain buyer-visible when share is unavailable. A finite persisted share must remain visible when `σ_k` is unavailable. Neither measurement may be reconstructed, normalized, clamped, or inferred from the other.

## Decision

Define one LineageWeave-owned report-axis badge projection with four states:

- combined: `leftover axis {axis} σ {value} {share}%`;
- singular only: `leftover axis {axis} σ {value}`;
- share only: `leftover axis {axis} {share}%`;
- neither usable: omit the badge.

The projection consumes persisted axis values only. `σ_k` is accepted only when finite and non-negative; `σ=0` remains explicit. Share uses the existing finite-value formatter. Missing or invalid evidence fails closed independently.

This decision changes presentation composition only. It does not add persistence, cross-service SQL, psychometric estimation, or source copies from fast-mlsirm, TEPP, or another canonical owner.

## Consequences

The report no longer needs to represent missing share as `NaN%`, and a singular-only axis remains inspectable. Existing combined and share-only buyer copy remains unchanged. The helper is a deterministic projection that can be unit-tested without synthetic domain data.

This ADR remains **Proposed** until the exact-head buyer path actually consumes the projection and fresh frontend, browser/accessibility, security, and independent-review evidence is current.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403. https://doi.org/10.1007/s11336-021-09762-5

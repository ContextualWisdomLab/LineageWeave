# ADR 0211 — Consume fast-mlsirm residual interaction maps

**Decision status:** Accepted
**Date:** 2026-08-25

## Context

LineageWeave previously computed a Gabriel factorization of post-evaluation
residuals locally. That violated the repository boundary: reusable
psychometric arithmetic belongs to fast-mlsirm, while this product owns domain
identifiers, authorization, persistence, and presentation.

## Decision

Pin and consume fast-mlsirm's versioned `residual_interaction_map` contract.
fast-mlsirm's Rust core exclusively computes `R = Y - E`, complete-case
admission, Gabriel coordinates, singular values, axis inertia, Euclidean map
distance, truncated reconstruction `Rhat`, `U = R - Rhat`, and the exact
algebraic cross term `2 Rhat U / R^2`.

LineageWeave passes the ADR-defined two reader-visible axes, maps returned row
and column indices to post and criterion identifiers, selects the deterministic
minimum and maximum returned distances, applies ABAC at persistence/read time,
and renders the supplied evidence. It does not reproduce any scientific
formula. Missing or non-finite upstream values remain unavailable.

The cross term is an auditable identity term, not a weight, threshold,
psychometric score, or heuristic.

## Consequences

- The numerical method is reusable across products and tested once in Rust.
- A missing or incompatible upstream contract fails closed; LineageWeave does
  not fall back to NumPy SVD or local arithmetic.
- Product tests mock sealed provider outputs to verify ID mapping and selection;
  fast-mlsirm owns numerical recovery and edge-case tests.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with application
to principal component analysis. *Biometrika, 58*(3), 453–467.
https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item-respondent interactions: A latent space item response model
with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

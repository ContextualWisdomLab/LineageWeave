# ADR 0119 — Measure leftover-map distances on two Gabriel axes

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md).

## Context

ADR 0048 persists closest and farthest leftover post–criterion pairs
after IRT main effects. Jeon et al. (2021, eq. 3) place the leftover
interaction `−γ‖ξ_p − ζ_i‖` on a two-dimensional person–item map.
Gabriel (1971) supplies those coordinates from a residual biplot.

`leftover_pairs.py` previously measured Euclidean distance on every
kept SVD axis. A rank-3 residual therefore reported a leftover
distance that a buyer cannot read on the 2D interaction map, and
that would disagree with stored two-axis coordinates if those later
persist. Rank-1 seed fixtures still
passed because unused axes were absent, not because the estimator
was two-dimensional.

## Decision

Closest and farthest leftover distances are Euclidean on **exactly
two** leftover-map axes. `_leftover_map_positions` may still return
the full Gabriel factorization; `_pad_map_axes` pads a rank-0 or
rank-1 map with zeros and truncates hidden axes after the second.
Missing cells stay out of the factorization. Rank-0 residuals still
emit a stable pair with distance zero. Do not invent a leftover
score. Do not invent a theta.

This slice does not persist map coordinates or change leftover UI.
Those remain ADR 0048 / 0049, and persist-map tables stay on their
own PR stack.

## Consequences

`leftover_distance` on `report_leftover_pair` matches the 2D Jeon
map. After `make seed`, closest and farthest pairs above the member
list still open that post. A rank-3 synthetic residual proves the
stored distance equals the two-axis hypot and is not the full-rank
norm.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

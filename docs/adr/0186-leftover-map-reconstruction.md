# ADR 0186 — Name leftover-map reconstruction on leftover pairs

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance `d = ‖ξ_p − ζ_i‖` and
leftover residual `R = Y − E[Y|θ, item]` on `report_leftover_pair`.
ADR 0049 already renders closest and farthest pairs above the member
list and opens the named post. Distance is the Jeon et al. (2021,
eq. 3) map gap. Gabriel (1971) reconstructs a *centered* matrix from
the biplot as the inner product of person and item coordinates. The
leftover map buyers read is two-axis: unused axes pad with zero, and
hidden SVD axes after the second are dropped. Two-axis reconstruction
`R̂_c = ξ_{1:2} · ζ_{1:2}` therefore recovers centered leftover
`R̃ = R − center`, not raw residual `R` and not leftover-map distance
`d`. Hiding `R̂_c` lets a buyer read distance as if it named how much
leftover the two leftover-map axes reconstruct.

This increment does not persist leftover-map coordinates, does not
persist leftover-map unexplained leftover `U` or `U_c`, does not
persist leftover-map explained leftover share `e`, unexplained leftover
share `s`, or leftover-map cross share `x`, does not name leftover-map
cosine or length, does not name observed `Y` / expected `E`, does not
name leftover-map rank, does not split leftover-map distance onto two
axes, and does not land Post quality on the leftover criterion.
Leftover-map distance stays two-axis Euclidean (ADR 0119).

The unprotected-stack reconstructions for neighbouring leftover facts
use 0162–0185. This protected-main increment uses **0186** so it does
not collide with leftover-map cross share (0185), leftover-map
explained leftover share (0184), leftover-map unexplained leftover
share (0183), leftover-map unexplained leftover (0182), leftover-map
length (0181 on the length stack), leftover-map cosine (0180),
leftover-map inner product (0179), leftover residual disclosure
(0162 / 0178), leftover observed `Y` / expected `E` (0163 / 0170),
leftover-map rank (0164 / 0172), two-axis leftover-map distance
(0119 / 0166), leftover coverage (0165 / 0168), leftover-map axis
share (0148), or leftover interaction-map persistence (0121).

## Decision

Each leftover pair names `leftover_map_reconstruction` — two-axis
Gabriel reconstruction `R̂_c = ξ_{1:2} · ζ_{1:2}` of centered leftover
after IRT main effects. Migration `0186` is the single source of the
column on every install path, fresh or existing -- shipped migrations
(`0001` / `0012`) are never edited after the fact. The column is
nullable so older leftover rows keep distance and residual without
fabricating a reconstruction. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.
A rank-0 origin map stores `0.0` (`ξ = 0`, `ζ = 0`), not a missing
value. A non-finite reconstruction stores null rather than inventing
a leftover score. A finite negative reconstruction is stored; do not
add a nonnegative CHECK. Do not persist
`leftover_map_explained_share`, `leftover_map_unexplained_share`,
`leftover_map_unexplained`, `leftover_map_cross_share`, or leftover-map
coordinates.

The pair button shows `R̂ {reconstruction}` next to leftover-map
distance `d` when the value is a finite number, including a signed
negative reconstruction. Next action: two leftover-map axes
reconstruct centered leftover `R̂` after IRT main effects; open this
post. A missing or non-finite reconstruction omits the badge and
keeps the existing closest/farthest next action. Do not invent a
leftover score or a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_reconstruction`. After `make seed`, closest and farthest
leftover pairs sit above the member list with leftover-map
reconstruction; click opens that post. Hidden posts stay hidden.

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual UI extraction, two-axis leftover-map
distance, leftover observed `Y` / expected `E`, leftover-map rank, and
leftover-map share identities.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

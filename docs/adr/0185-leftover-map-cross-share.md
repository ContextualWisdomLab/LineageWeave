# ADR 0185 — Name leftover-map cross share on period-report pair rows

**Decision status:** Draft
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
`R̃ = R − center`, not raw residual `R`. Truncated two-axis
reconstruction of a higher-rank cell keeps unexplained leftover
`U_c = R̃ − R̂_c` and a cross term `2 R̂_c U_c`. The cell identity
`R̃² = R̂_c² + U_c² + 2 R̂_c U_c` therefore yields
`e + s + x = 1` with explained leftover share `e = R̂_c² / R̃²`,
unexplained leftover share `s = U_c² / R̃²`, and leftover-map cross
share `x = 2 R̂_c U_c / R̃²`. Hiding `x` lets a buyer read `e + s`
as a complete leftover partition even though the truncated map leaves
an identity remainder. `x` may be negative when reconstruction and
unexplained leftover have opposite signs; a nonnegative CHECK would
reject a mathematically honest cell.

This increment does not persist leftover-map reconstruction `R̂` or
`R̂_c`, does not persist leftover-map unexplained leftover `U` or
`U_c`, does not persist leftover-map unexplained leftover share `s`,
does not persist leftover-map explained leftover share `e`, does not
persist leftover-map coordinates, does not name leftover-map inner
product, cosine, or length, does not name observed `Y` / expected
`E`, does not name leftover-map rank, does not split leftover-map
distance onto two axes, and does not land Post quality on the leftover
criterion. Leftover-map distance stays full-rank Euclidean.
Reconstruction `R̂_c` and unexplained leftover `U_c` are computed
internally so `x` is honest, then discarded.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0162–0184. This protected-main increment uses **0185** so it does
not collide with leftover-map explained leftover share (0184),
leftover-map unexplained leftover share (0183), leftover-map
unexplained leftover (0182), leftover-map reconstruction (0181),
leftover-map length (0181 on the length stack), leftover-map cosine
(0180), leftover-map inner product (0179), leftover residual
disclosure (0178), leftover observed `Y` / expected `E` (0170),
leftover-map rank (0172), two-axis leftover-map distance (0166),
leftover coverage (0165 / 0168), leftover-map axis share (0148), or
leftover interaction-map persistence (0121).

## Decision

Each leftover pair names `leftover_map_cross_share` — leftover-map
cross share `x = 2 R̂_c U_c / R̃²` of centered leftover after
two-axis Gabriel reconstruction `R̂_c = ξ_{1:2} · ζ_{1:2}` and
unexplained leftover `U_c = R̃ − R̂_c`. Migration `0185` is the
single source of the column on every install path, fresh or existing
-- shipped migrations (`0001` / `0012`) are never edited after the
fact. The column is nullable so older leftover rows keep distance and
residual without fabricating a share. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.
A rank-0 origin map stores `0.0` (`R̃ = 0`, `R̂_c = 0`, `U_c = 0`),
not a missing value. A fully reconstructed rank-1 cell stores `0.0`
because `U_c = 0`. A non-finite share stores null rather than
inventing a leftover score. A finite negative share is stored; do not
add a nonnegative CHECK. Do not persist
`leftover_map_explained_share`, `leftover_map_unexplained_share`,
`leftover_map_unexplained`, or `leftover_map_reconstruction`.

The pair button shows `2R̂U/R̃² {share}` next to leftover-map
distance `d` when the value is a finite number, including a signed
negative remainder. Next action: two leftover-map axes leave identity
remainder `x` of centered leftover after IRT main effects; open this
post to read the named criterion. A missing or non-finite share omits
the badge and keeps the existing closest/farthest next action. Do not
invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_cross_share`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `2R̂U/R̃²` next
to `d`; click opens that post. Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map reconstruction,
leftover-map unexplained leftover, leftover-map unexplained leftover
share, and leftover-map explained leftover share.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

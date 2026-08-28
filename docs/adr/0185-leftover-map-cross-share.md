# ADR 0185 — Name leftover-map cross share on period-report pair rows

**Decision status:** Draft
**Date:** 2026-08-24
**Amended by:** [ADR 0266](0266-leftover-map-explained-share.md) (leftover-map explained share `e = R̂² / R²`)

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance `d = ‖ξ_p − ζ_i‖` and
leftover residual `R = Y − E[Y|θ, item]` on `report_leftover_pair`.
ADR 0049 already renders closest and farthest pairs above the member
list and opens the named post. Distance is the Jeon et al. (2021,
eq. 3) map gap. Gabriel (1971) derives coordinates from the centered
matrix, while ADR 0182 defines the auditable cell reconstruction as
`R̂ = ξ_{1:2} · ζ_{1:2}` and unexplained leftover as `U = R − R̂`.
The leftover map is two-axis: unused axes pad with zero, and hidden SVD
axes after the second are dropped. The raw-residual cell identity
`R² = R̂² + U² + 2 R̂ U` therefore yields
`e + s + x = 1` with explained leftover share `e = R̂² / R²`,
unexplained leftover share `s = U² / R²`, and leftover-map cross
share `x = 2 R̂ U / R²`. Hiding `x` lets a buyer read `e + s`
as a complete leftover partition even though the truncated map leaves
an identity remainder. `x` may be negative when reconstruction and
unexplained leftover have opposite signs; a nonnegative CHECK would
reject a mathematically honest cell.

This increment does not persist leftover-map reconstruction `R̂`, does
not add another unexplained-leftover column, does not persist
leftover-map unexplained leftover share `s`,
does not persist leftover-map explained leftover share `e`, does not
persist leftover-map coordinates, does not name leftover-map inner
product, cosine, or length, does not name observed `Y` / expected
`E`, does not name leftover-map rank, does not split leftover-map
distance onto two axes, and does not land Post quality on the leftover
criterion. Leftover-map distance stays full-rank Euclidean.
Reconstruction `R̂` is computed internally so `x` reconciles with the
persisted raw residual and ADR 0182 unexplained leftover.

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
cross share `x = 2 R̂ U / R²` of raw residual after
two-axis Gabriel reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}` and
unexplained leftover `U = R − R̂`. Migration `0185` is the
single source of the column on every install path, fresh or existing
-- shipped migrations (`0001` / `0012`) are never edited after the
fact. The column is nullable so older leftover rows keep distance and
residual without fabricating a share. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.
A rank-0 origin cell stores `0.0` when `R = R̂ = U = 0`, not a missing
value. A rank-1 cell may retain a nonzero raw-residual cross term when
centering removed a nonzero mean. A non-finite share stores null rather than
inventing a leftover score. A finite negative share is stored; do not
add a nonnegative CHECK. This increment does not introduce
`leftover_map_explained_share`, `leftover_map_unexplained_share`, or
`leftover_map_reconstruction`; ADR 0182 remains authoritative for
`leftover_map_unexplained`.

The pair button shows `2R̂U/R² {share}` next to leftover-map
distance `d` when the value is a finite number, including a signed
negative remainder. Next action: two leftover-map axes leave identity
remainder `x` of raw residual after IRT main effects; open this
post to read the named criterion. A missing or non-finite share omits
the badge and keeps the existing closest/farthest next action. Do not
invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_cross_share`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `2R̂U/R²` next
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

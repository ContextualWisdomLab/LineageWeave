# ADR 0182 — Name unexplained leftover on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-24

**Amended by:** [ADR 0201](0201-leftover-map-reconstruction.md)
(two-axis reconstruction R̂);
[ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)
(leftover-map unexplained leftover on graphic-display pair segments)

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance `d = ‖ξ_p − ζ_i‖` and
leftover residual `R = Y − E[Y|θ, item]` on `report_leftover_pair`.
ADR 0049 already renders closest and farthest pairs above the member
list and opens the named post. Distance is the Jeon et al. (2021,
eq. 3) map gap. Gabriel (1971) reconstructs a matrix from the biplot
as the inner product of person and item coordinates. The leftover map
buyers read is two-axis: unused axes pad with zero, and hidden SVD
axes after the second are dropped. Two-axis reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}` is therefore the leftover cell the map
shows. Hiding unexplained leftover `U = R − R̂` lets a buyer read
leftover residual `R` or leftover-map distance `d` as the leftover
the two-axis map does not reconstruct.

At ADR 0182's initial acceptance, this increment did not persist
leftover-map reconstruction `R̂`; ADR 0201 now persists that value so
`U + R̂ = R` remains directly auditable. It still does
not persist leftover-map coordinates, does not name leftover-map inner
product as a separate full-rank column, does not name leftover-map
cosine, does not name leftover-map length, does not name observed `Y` /
expected `E`, does not name leftover-map rank, does not split leftover-map
distance onto two axes, and does not land Post quality on the leftover
criterion. Leftover-map distance stays full-rank Euclidean.
Reconstruction `R̂` is computed internally so `U` is honest and is now
retained under ADR 0201.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0162–0181. This protected-main increment uses **0182** so it does
not collide with leftover-map reconstruction (0181), leftover-map
length (0181 on the length stack), leftover-map cosine (0180),
leftover-map inner product (0179), leftover residual disclosure
(0178), leftover observed `Y` / expected `E` (0177), leftover-map
rank (0172), two-axis leftover-map distance (0166), leftover coverage
(0168), leftover-map axis share (0148), or leftover interaction-map
persistence (0121).

## Decision

Each leftover pair names `leftover_map_unexplained` — unexplained
leftover `U = R − R̂` after two-axis Gabriel reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}`. Migration `0182` is the single source of
the column on every install path, fresh or existing -- shipped
migrations (`0001` / `0012`) are never edited after the fact. The
column is nullable so older leftover rows keep distance and residual
without fabricating unexplained leftover. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.
A rank-0 origin map stores `0.0` (`R = 0` and `R̂ = 0`), not a
missing value. A non-finite unexplained leftover stores null rather
than inventing a leftover score. Persist
`leftover_map_reconstruction` so `U + R̂ = R` stays auditable.

The pair button shows `U {signed}` next to leftover-map distance `d`
when the value is finite. Next action: leftover map leaves unexplained
`U` after IRT main effects; open this post to read the named criterion.
A missing or non-finite unexplained leftover omits the badge and keeps
the existing closest/farthest next action. Do not invent a leftover
score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_unexplained`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `U` next to `d`;
click opens that post. Hidden posts stay hidden. ADR 0276
captions leftover-map graphic-display pair segments with the same
persisted leftover-map unexplained leftover; it adds no columns.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, and leftover-map
reconstruction.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

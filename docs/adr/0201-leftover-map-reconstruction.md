# ADR 0201 — Name leftover-map reconstruction on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-25
**Amended by:** [ADR 0266](0266-leftover-map-explained-share.md) (leftover-map explained share `e = R̂² / R²`)

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0049](0049-leftover-pair-report-ui.md), and
[ADR 0182](0182-leftover-map-unexplained.md). Independent of landed
complete-case coverage ([ADR 0168](0168-leftover-map-complete-case-coverage.md)).

## Context

ADR 0182 already persists unexplained leftover `U = R − R̂` after
two-axis Gabriel reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}`. That
reconstruction is computed internally so `U` is honest, then discarded.
A buyer who reads `U` next to leftover residual `R` cannot check
`U + R̂ = R` without the reconstruction the two-axis map actually
uses. Hiding `R̂` lets leftover residual `R` or leftover-map distance
`d` be read as the leftover the map reconstructs.

This increment persists leftover-map reconstruction `R̂`. It does not
persist leftover-map coordinates, does not name leftover-map inner
product as a separate full-rank column, does not name leftover-map
cosine, does not name leftover-map length, does not name leftover-map
explained share or unexplained share, and does not land
Post quality on the leftover criterion. Leftover-map distance stays
two-axis Euclidean. Reconstruction is the same internal two-axis inner
product already used for `U`, so `U + R̂ = R` remains true. Do not
substitute a separately centered reconstruction `R̃` that would break
that identity. ADR 0185 independently persists the raw-residual cross
share derived from this same `R̂` and `U`; this decision exposes `R̂`
without changing that formula.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0162–0181 and 0184–0186. This protected-main increment uses
**0206** so it does not collide with source-post event time
(0183), leftover-map reconstruction on the centered stack (0186),
leftover-map unexplained share (0184 on that stack), leftover-map
explained share, leftover-map cross share, leftover residual
disclosure, leftover observed `Y` / expected `E`, leftover-map rank,
two-axis leftover-map distance, leftover coverage, leftover-map axis
share (0148), or leftover interaction-map persistence.

## Decision

Each leftover pair names `leftover_map_reconstruction` — two-axis
Gabriel reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}`. Unused axes pad with
zero. Hidden SVD axes after the second are dropped. Migration `0206`
is the single source of the column on every install path, fresh or
existing -- shipped migrations (`0001` / `0012`) are never edited after
the fact. The column is nullable so older leftover rows keep distance,
residual, and unexplained leftover without fabricating reconstruction.
Fallback pairs that have no complete-case leftover map omit the value
rather than inventing one. A rank-0 map stores `0.0` for `R̂`; raw residual
`R` may be a nonzero constant after centering, in which case `U = R` and
`U + R̂ = R` still holds. A non-finite reconstruction stores
null rather than inventing a leftover score. A signed reconstruction
is stored, never clamped. Do not add a nonnegative CHECK.

The pair button shows `R̂ {signed}` next to leftover-map distance `d`
when the value is finite. Next action: leftover map reconstructs `R̂`
after IRT main effects; open this post to read the named criterion.
A missing or non-finite reconstruction omits the badge and keeps the
existing unexplained-leftover next action. Do not invent a leftover
score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_reconstruction`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `R̂` next to `d`;
click opens that post. Hidden posts stay hidden. When both
reconstruction and unexplained leftover are finite,
`U + R̂ = R`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map unexplained
share, leftover-map explained share, leftover-map cross share, and
the centered leftover-map reconstruction stack.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

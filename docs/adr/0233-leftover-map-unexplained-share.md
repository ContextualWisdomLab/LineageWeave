# ADR 0233 — Name leftover-map unexplained leftover share on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-27

**Amended by:** [ADR 0266](0266-leftover-map-explained-share.md)
(explained leftover share e)

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md). Independent of leftover-map
cross share ([ADR 0185](0185-leftover-map-cross-share.md)) and leftover-map
reconstruction ([ADR 0201](0201-leftover-map-reconstruction.md)).

## Context

ADR 0182 already persists unexplained leftover `U = R − R̂` after
two-axis Gabriel reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}`. ADR 0185
already persists leftover-map cross share `x = 2 R̂ U / R²`. The
raw-residual cell identity `R² = R̂² + U² + 2 R̂ U` therefore yields
`e + s + x = 1` with explained leftover share `e = R̂² / R²` and
unexplained leftover share `s = U² / R²`. Hiding `s` lets a buyer
read leftover residual `R`, leftover-map distance `d`, or unexplained
leftover `U` as the leftover the truncated map cannot reconstruct,
even though `s` is the square share of that leftover.

This increment persists leftover-map unexplained leftover share `s`.
Leftover-map explained leftover share `e` is persisted independently by
[ADR 0266](0266-leftover-map-explained-share.md). It does not persist leftover-map coordinates, does not name leftover-map inner
product, cosine, or length, and does not land Post quality on the
leftover criterion. Leftover-map distance stays two-axis Euclidean.
Reconstruction `R̂` and unexplained leftover `U` remain the same
internal two-axis terms already used for `x`, so `e + s + x = 1`
stays auditable from persisted `R`, `R̂`, `U`, `x`, and `s`.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0183 for unexplained leftover share. The dashboard stack already
uses **0266** for leftover-map explained leftover share and
**0222** for operations-case analysis input. This protected-main
increment uses **0233** (migration **0233**) so it does not collide with
GNB chrome (0183), ontology explorer (0184), leftover-map cross share
(0185), leftover-map reconstruction (0201 / migration 0206), leftover
residual disclosure, leftover observed `Y` / expected `E`, leftover-map
rank, two-axis leftover-map distance, leftover coverage, leftover-map
axis share (0148), leftover interaction-map persistence, leftover-map
explained leftover share (ADR 0266), or
operations-case analysis input (0222 on that stack).

## Decision

Each leftover pair names `leftover_map_unexplained_share` — leftover-map
unexplained leftover share `s = U² / R²` of raw residual after
two-axis Gabriel reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}` and
unexplained leftover `U = R − R̂`. Migration `0233` is the
single source of the column on every install path, fresh or existing
-- shipped migrations (`0001` / `0012`) are never edited after the
fact. The column is nullable so older leftover rows keep distance,
residual, unexplained leftover, reconstruction, and cross share
without fabricating a share. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.
A rank-0 origin cell stores `0.0` when `R = R̂ = U = 0`, not a missing
value. A rank-0 constant residual with `R̂ = 0` stores `1.0` (`s = U² / R²`
with `U = R`). A non-finite share stores null rather than inventing a
leftover score. `s` is nonnegative because it is a square share; a
finite share greater than 1 is stored when `|U| > |R|`. Do not add an
upper-bound CHECK. Leftover-map explained leftover share `e` is
persisted independently by ADR 0266.

The pair button shows `U²/R² {share}` next to leftover-map
distance `d` when the value is a finite number. Next action: leftover
map leaves unexplained leftover share `s` of raw residual after IRT
main effects; open this post to read the named criterion. A missing
or non-finite share omits the badge and keeps the existing
cross-share / reconstruction / unexplained-leftover next action. Do
not invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_unexplained_share`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `U²/R²` next
to `d`; click opens that post. Hidden posts stay hidden. When `R`,
`R̂`, `U`, `x`, and `s` are all finite, `e + s + x = 1` with
`e = R̂² / R²` computed internally.

The grouping comparison strip (ADR 0149) stays on its reduced leftover
payload (distance, residual, reconstruction). Unexplained leftover
share is a period-report pair fact, not a comparison-strip badge.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map reconstruction,
leftover-map unexplained leftover, leftover-map cross share, and
leftover-map explained leftover share.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

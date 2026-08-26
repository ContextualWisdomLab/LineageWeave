# ADR 0232 — Name leftover-map explained share on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-27

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0049](0049-leftover-pair-report-ui.md),
[ADR 0185](0185-leftover-map-cross-share.md), and
[ADR 0201](0201-leftover-map-reconstruction.md). Independent of leftover-map
unexplained leftover ([ADR 0182](0182-leftover-map-unexplained.md)).

## Context

ADR 0185 already persists leftover-map cross share
`x = 2 R̂ U / R²` of raw residual after two-axis Gabriel reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}` and unexplained leftover `U = R − R̂`. ADR 0201
already persists signed reconstruction `R̂` so `U + R̂ = R` stays
auditable. The raw-residual cell identity
`R² = R̂² + U² + 2 R̂ U` therefore yields
`e + s + x = 1` with explained leftover share `e = R̂² / R²`,
unexplained leftover share `s = U² / R²`, and leftover-map cross
share `x`. Hiding `e` lets a buyer read `x` (or `R̂`) as the leftover
the two-axis map explains. `e` is nonnegative when finite. Truncated
two-axis reconstruction of a higher-rank cell can make `|R̂| > |R|`, so
a finite explained share may exceed 1; a unit CHECK would reject a
mathematically honest cell.

This increment does not persist leftover-map unexplained leftover share
`s`, does not persist leftover-map coordinates, does not name leftover-map
inner product, cosine, or length, and does not land Post quality on the
leftover criterion. Leftover-map distance stays two-axis Euclidean.
Reconstruction `R̂` remains the ADR 0201 internal two-axis inner
product already used for `U` and `x`.

The feature is stacked over the Rust-boundary work in ADR 0208. The decision
number remains 0232, while the schema increment uses migration **0236** so it
does not collide with the parent stack's migrations. It also does not collide
with leftover-map reconstruction (0201 / migration 0206),
leftover-map cross share (0185), leftover-map unexplained leftover
(0182), leftover-map unexplained leftover share, leftover residual
disclosure, leftover observed `Y` / expected `E`, leftover-map rank,
two-axis leftover-map distance, leftover coverage, leftover-map axis
share (0148), leftover interaction-map persistence, or shared
token-backed status notice (0214 on an open stack).

## Decision

fast-mlsirm's Rust `residual_interaction_map` computes the reconstruction,
unexplained residual, cross share, and explained share in one result envelope.
LineageWeave only binds those returned cells to authorized product identifiers;
it never recalculates these quantities in Python.

Each leftover pair names `leftover_map_explained_share` — leftover-map
explained share `e = R̂² / R²` of raw residual after two-axis Gabriel
reconstruction `R̂ = ξ_{1:2} · ζ_{1:2}`. Migration `0236` is the
single source of the column on every install path, fresh or existing --
shipped migrations (`0001` / `0012`) are never edited after the fact.
The column is nullable so older leftover rows keep distance, residual,
unexplained leftover, cross share, and reconstruction without
fabricating a share. Fallback pairs that have no complete-case leftover
map omit the value rather than inventing one. A rank-0 origin cell
stores `0.0` when `R = R̂ = 0`, not a missing value. A non-finite
share stores null rather than inventing a leftover score. A finite
share greater than 1 is stored; do not add a unit or nonnegative CHECK.
This increment does not introduce `leftover_map_unexplained_share`.

The pair button shows `R̂²/R² {share}` next to leftover-map distance
`d` when the value is a finite number. Next action: leftover map
explains `{share}` of raw residual after IRT main effects; open this
post to read the named criterion. Explained leftover share takes
priority over leftover-map cross share when both are finite. A missing
or non-finite share omits the badge and keeps the existing cross-share
next action. Do not invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_explained_share`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `R̂²/R²` next to
`d`; click opens that post. Hidden posts stay hidden. When explained
share, unexplained leftover, reconstruction, and cross share are all
finite and `R ≠ 0`, `e + s + x = 1` with `s = U² / R²` computed only
for the audit identity, not persisted.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map unexplained
share, leftover-map unexplained leftover, leftover-map reconstruction,
and leftover-map cross share.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

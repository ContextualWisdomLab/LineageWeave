# ADR 0048 — Persist LSIRM leftover post–criterion pairs

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0119](0119-leftover-map-two-dimensional-distance.md) (two leftover-map axes);
[ADR 0163](0163-leftover-observed-expected.md) (observed Y and expected E);
[ADR 0164](0164-leftover-map-rank.md) (full map rank);
[ADR 0182](0182-leftover-map-unexplained.md) (unexplained leftover U);
[ADR 0185](0185-leftover-map-cross-share.md) (leftover-map cross share);
[ADR 0201](0201-leftover-map-reconstruction.md) (signed reconstruction R̂);
[ADR 0233](0233-leftover-map-unexplained-share.md) (unexplained leftover share s);
[ADR 0266](0266-leftover-map-explained-share.md) (explained leftover share e);
[ADR 0267](0267-leftover-map-coordinates.md) (leftover-map coordinates ξ, ζ);
[ADR 0268](0268-leftover-map-graphic-display.md) (leftover-map graphic display);
[ADR 0269](0269-leftover-map-axis-share-plot.md) (leftover-map axis share on the graphic display);
[ADR 0270](0270-leftover-map-coordinate-ticks.md) (leftover-map coordinate ticks);
[ADR 0271](0271-leftover-map-segment-distance.md) (leftover-map distance on pair segments);
[ADR 0272](0272-leftover-map-segment-reconstruction.md) (leftover-map reconstruction on pair segments);
[ADR 0273](0273-leftover-map-segment-explained-share.md) (leftover-map explained leftover share on pair segments);
[ADR 0274](0274-leftover-map-segment-unexplained-share.md) (leftover-map unexplained leftover share on pair segments);
[ADR 0275](0275-leftover-map-segment-cross-share.md) (leftover-map cross share on pair segments);
[ADR 0276](0276-leftover-map-segment-unexplained-leftover.md) (leftover-map unexplained leftover on pair segments)

## Context

Period reports already persist IRT main effects: EAP θ per post, a
shared GRM/GPCM item bank, FIPC linking, and Lord (1980) max-info CAT
ranks. After those main effects, Jeon et al. (2021, eq. 3) leave a
leftover interaction `−γ‖ξ_p − ζ_i‖` on the person–item map. Closest
pairs are the smallest Euclidean leftover-map distances; farthest
pairs are the largest.

`fast-mlsirm` implements the leftover term inside MLSRM fitting but
exposes no leftover-pair API. LineageWeave must not fork LSIRM or
invent a second IRT fit. Buyers still need a durable, clickable
answer to “which post–criterion pair is unexpectedly aligned, and
which pair is unexpectedly opposed?”

## Decision

After a real GRM/GPCM score, compute the residual matrix
`R = Y − E[Y|θ, item]` from the already-fitted category
probabilities. A Gabriel (1971) biplot of the **complete-case**
submatrix of `R` supplies person positions `ξ` and item positions
`ζ`. Missing response cells are excluded from the factorization;
they are never filled with zero. Persist exactly one `closest`
and one `farthest` observed cell per period report in
`report_leftover_pair` (3NF, two-or-more-word `snake_case`).

tests do not import `period_report` or `fast_mlsirm`. Distances are
Euclidean on the two leftover-map axes (ADR 0119). Each leftover row
also names observed `Y` and expected `E[Y|θ, item]` so residual
reconciles to `Y − E` (ADR 0163), and names the full singular-value
rank while distance remains on the first two axes (ADR 0164). Each
leftover row also names unexplained leftover `U = R − R̂` when
Gabriel coordinates exist so the leftover cell the two-axis map does
not reconstruct is not read as leftover residual `R` or leftover-map
distance `d` (ADR 0182), and names leftover-map cross share
`x = 2 R̂ U / R²` of raw residual when Gabriel coordinates
exist so the identity remainder after two-axis reconstruction is not
read as leftover residual `R`, leftover-map distance `d`, explained
leftover share `e`, or unexplained leftover share `s` (ADR 0185).
ADR 0201 now persists that same signed reconstruction on the pair row so
`U + R̂ = R` remains directly auditable; it does not change this selection or
distance contract. ADR 0233 persists unexplained leftover share
`s = U² / R²` of raw residual so the leftover the truncated map cannot
reconstruct is not read as leftover residual `R`, leftover-map distance
`d`, unexplained leftover `U`, or leftover-map cross share `x`. ADR 0266
persists leftover-map explained leftover share `e = R̂² / R²` of raw
residual so the leftover the truncated map reconstructs is not read as
leftover residual `R`, leftover-map distance `d`, unexplained leftover
`U`, leftover-map cross share `x`, or unexplained leftover share `s`.
When `R`, `R̂`, `U`, `x`, `s`, and `e` are finite, `e + s + x = 1`.
ADR 0267 persists leftover-map coordinates `ξ_{1:2}` and `ζ_{1:2}` so
reconstruction `R̂ = ξ · ζ` and distance `d = ‖ξ − ζ‖` stay auditable
from the pair row. ADR 0268 draws those persisted coordinates as the
leftover-map graphic display; it adds no columns. ADR 0269 captions
those leftover-map axes with persisted leftover-map axis share; it
adds no columns. ADR 0270 ticks leftover-map axes at persisted `ξ` /
`ζ` coordinates; it adds no columns. ADR 0271 captions leftover-map
pair segments with persisted leftover-map distance `d`; it adds no
columns. ADR 0272 captions leftover-map pair segments with persisted
leftover-map reconstruction `R̂`; it adds no columns. ADR 0273 captions
leftover-map pair segments with persisted leftover-map explained leftover
share `e`; it adds no columns. ADR 0274 captions leftover-map pair
segments with persisted leftover-map unexplained leftover share `s`; it
adds no columns. ADR 0275 captions leftover-map pair segments with
persisted leftover-map cross share `x`; it adds no columns. ADR 0276
captions leftover-map pair segments with persisted leftover-map
unexplained leftover `U`; it adds no columns.

Cascade the rows with `report_period_score`. A leftover post must
also be a `report_member_score` row, and the leftover criterion
must be a `report_item_information` item on that same report.
Do not store a second theta. Do not invent leftover numbers when
the IRT matrix is unusable. A rank-0 residual still emits a
stable pair so `make seed` is not empty; the stored distance is
then zero, not a fabricated interaction.

The UI contract is ADR 0049. Complete-case coverage is ADR 0168.

## Consequences

Rebuild and seed write leftover pairs in the same transaction as
member scores. `GET /api/reports/{grouping}/{period}` returns
`leftover_pairs` with the post title so the buyer can open that post.
Hidden posts stay hidden: leftover pairs join `source_post` and use
the same ABAC gate as members. Migration `0012_report_leftover_pair.sql`
upgrades volumes that already applied `0001`.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

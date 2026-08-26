# ADR 0048 — Persist LSIRM leftover post–criterion pairs

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0119](0119-leftover-map-two-dimensional-distance.md) (two leftover-map axes);
[ADR 0163](0163-leftover-observed-expected.md) (observed Y and expected E);
[ADR 0164](0164-leftover-map-rank.md) (full map rank);
[ADR 0182](0182-leftover-map-unexplained.md) (unexplained leftover U);
[ADR 0185](0185-leftover-map-cross-share.md) (leftover-map cross share);
[ADR 0201](0201-leftover-map-reconstruction.md) (signed reconstruction R̂);
[ADR 0232](0232-leftover-map-explained-share.md) (leftover-map explained share)

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
distance contract. ADR 0232 persists leftover-map explained share
`e = R̂² / R²` of raw residual so `e + s + x = 1` is not read from `x`
alone; unexplained leftover share `s` is still not persisted.

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

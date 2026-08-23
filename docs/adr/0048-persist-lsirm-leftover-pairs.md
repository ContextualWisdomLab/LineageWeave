# ADR 0048 — Persist LSIRM leftover post–criterion pairs

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0164](0164-leftover-map-rank.md) (leftover-map rank)

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

The biplot lives in `lineageweave/leftover_pairs.py` so leftover
tests do not import `period_report` or `fast_mlsirm`. Each leftover
row also names leftover-map rank so a rank-0 collapse is not read as
leftover structure (ADR 0164).

Cascade the rows with `report_period_score`. A leftover post must
also be a `report_member_score` row, and the leftover criterion
must be a `report_item_information` item on that same report.
Do not store a second theta. Do not invent leftover numbers when
the IRT matrix is unusable. A rank-0 residual still emits a
stable pair so `make seed` is not empty; the stored distance is
then zero, not a fabricated interaction.

The UI contract is ADR 0049.

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

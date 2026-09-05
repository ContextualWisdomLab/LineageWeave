# ADR 0305 — Return leftover-map rank on grouping comparison leftover pairs

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map rank
([ADR 0164](0164-leftover-map-rank.md)), leftover-map rank on grouping comparison
strip pair rows ([ADR 0301](0301-leftover-map-compare-rank.md)), leftover-map
axis share on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-axis-share.md)), leftover-map coordinates
on grouping comparison leftover-pair payload
([ADR 0303](0303-leftover-map-compare-coordinates-payload.md)), leftover-map
coordinates on grouping comparison strip pair rows
([ADR 0302](0302-leftover-map-compare-coordinates.md)), leftover expected on
grouping comparison strip pair rows
([ADR 0300](0300-leftover-map-compare-expected.md)), leftover observed on grouping
comparison strip pair rows
([ADR 0299](0299-leftover-map-compare-observed.md)), leftover residual on grouping
comparison strip pair rows
([ADR 0298](0298-leftover-map-compare-residual.md)), leftover-map rank on pair
segments ([ADR 0280](0280-leftover-map-segment-rank.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover observed
`Y` / expected `E` ([ADR 0163](0163-leftover-observed-expected.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
and leftover-map graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)).

## Context

ADR 0164 already persists leftover-map rank on leftover pair rows. ADR 0301 already
captions that persisted rank on grouping comparison leftover-pair buttons through
formatLeftoverMapRank. The period-report detail payload already returns
`leftover_map_rank`. `GET /api/reports/compare/{period}` still omits that column,
so every live grouping comparison leftover-pair button fail-closes the leftover-map
comparison rank badge even after the pair list and graphic already name `rank k`.
Hiding rank on the live strip lets leftover-map coordinates, leftover expected `E`,
leftover observed `Y`, leftover residual `R`, leftover-map reconstruction `R̂`, or
leftover-map distance `d` be read as leftover-map structure without a next action.

This increment returns persisted leftover-map rank on each grouping comparison
leftover pair, matching the detail-report payload. It does not add columns. It
does not invent leftover-map rank from leftover-map coordinates, leftover-map
distance, leftover expected, leftover observed, leftover residual, leftover-map
reconstruction, leftover-map axis share, leftover-map post coverage, leftover-map
item coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. It does not persist leftover-map inner
product, cosine, or length as separate columns. Do not invent a leftover score.
Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other numbers.
This protected increment uses **0305** so it does not collide with leftover-map
axis share on the grouping comparison strip (0304), leftover-map coordinates on
grouping comparison leftover-pair payload (0303), leftover-map coordinates on
grouping comparison strip pair rows (0302), leftover-map rank on grouping
comparison strip pair rows (0301), leftover-map rank on pair segments (0280),
leftover-map rank persistence (0164), leftover-map graphic display (0268), or the
dashboard stacks.

## Decision

On `GET /api/reports/compare/{period}`, include persisted `leftover_map_rank` on
each leftover pair, converting a stored integer the same way as
`GET /api/reports/{grouping}/{period}` and preserving nulls. A missing, negative,
or non-integer rank stays null (the formatter omits that leftover-map comparison
rank badge) and does not invent rank from leftover-map coordinates, leftover-map
distance, leftover expected, leftover observed, leftover residual, leftover-map
reconstruction, leftover-map unexplained leftover, leftover-map explained leftover
share, leftover-map unexplained leftover share, leftover-map cross share, leftover-map
axis share, leftover-map post coverage, leftover-map item coverage, leftover-map
incomplete post coverage, leftover-map incomplete item coverage, or the count of
unused axes. Rank-0 origin cells still return `0` when that persisted rank is stored.
A finite negative leftover on neighbouring fields is shown, never clamped. Do not add
the leftover-map graphic to the strip. Click a leftover pair on the strip to open
that post.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover score.
Do not invent a theta.

## Consequences

After `make seed`, `GET /api/reports/compare/{period}` leftover pairs include
persisted leftover-map rank when that rank was stored, so grouping comparison
leftover-pair buttons that already caption formatLeftoverMapRank can match the
pair-row rank badge on live responses. Closest and farthest leftover pairs still
sit above the member list with the leftover-map graphic display; click a post
marker or a pair button opens that post.
Hidden posts stay hidden. When `Y`, `E`, and `R` are finite, `Y − E = R`.
When `R`, `R̂`, and `U` are finite, `U + R̂ = R`.
When `R`, `R̂`, `U`, `x`, `s`, and `e` are finite, `e + s + x = 1`.
When coordinates, reconstruction, and distance are finite, `R̂ = ξ · ζ`
and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map complete-case
coverage persistence, leftover-map axis share persistence, leftover pairs on
the grouping comparison strip, leftover-map complete-case coverage on the
grouping comparison strip, leftover-map item complete-case coverage on the
grouping comparison strip, leftover-map incomplete post coverage on the grouping
comparison strip, leftover-map incomplete item coverage on the grouping
comparison strip, leftover-map reconstruction on grouping comparison strip pair
rows, leftover-map explained leftover share on grouping comparison strip pair
rows, leftover-map unexplained leftover share on grouping comparison strip pair
rows, leftover-map cross share on grouping comparison strip pair rows, leftover-map
unexplained leftover on grouping comparison strip pair rows, leftover residual on
grouping comparison strip pair rows, leftover observed on grouping comparison
strip pair rows, leftover expected on grouping comparison strip pair rows,
leftover-map rank on grouping comparison strip pair rows, leftover-map coordinates
on grouping comparison strip pair rows, leftover-map coordinates on grouping
comparison leftover-pair payload, leftover-map axis share on the grouping
comparison strip, leftover-map inner product, leftover-map cosine, leftover-map
length, leftover-map graphic display, leftover-map rank on pair segments, leftover-map
rank persistence, leftover-map coordinate persistence, leftover-map coordinate
ticks, leftover-map reconstruction persistence, leftover residual on pair segments,
leftover observed on pair segments, leftover expected on pair segments, leftover-map
item complete-case coverage on the graphic display, leftover-map item complete-case
coverage on the pair list, leftover-map incomplete post coverage on the graphic
display, leftover-map incomplete post coverage on the pair list, leftover-map
incomplete item coverage on the graphic display, leftover-map incomplete item
coverage on the pair list, and leftover-map post complete-case coverage fail-closed
on the pair list.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Leftover-map rank is
the number of residual SVD axes with nonzero singular value. Grouping comparison
leftover-map rank returns that persisted rank on `GET /api/reports/compare/{period}`
leftover pairs only when the stored rank is present. Rank-0 origin cells still
return `0` when that rank is stored.)

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

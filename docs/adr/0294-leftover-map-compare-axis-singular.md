# ADR 0294 — Name leftover-map singular values on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover-map axis share on the grouping comparison strip
([ADR 0293](0293-leftover-map-compare-axis-share.md)) and leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).
Independent of leftover-map incomplete item coverage on the grouping
comparison strip ([ADR 0292](0292-leftover-map-compare-incomplete-item.md))
and leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)). The dashboard plot stack
already named leftover-map singular values on graphic axes and leftover-axis
badges under other numbers; this protected increment uses **0294**.

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²` on `report_leftover_map_axis`. ADR 0293 already
includes those persisted axes on `GET /api/reports/compare/{period}` and
captions leftover-map axis share on the grouping comparison strip. The strip
still names share without naming leftover-map singular value for that
grouping, so a buyer who compares PU / corp / thread leftover pairs can treat
an 82% first axis as if it had the same Gabriel scale as a rank-0 unused axis.

This increment captions each grouping row through leftoverMapCompareAxisSingular.
It does not add columns. It does not invent leftover-map singular value from
leftover-map axis share, leftover pair count, plotted marker count, leftover-map
distance, leftover-map rank, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. It does not persist leftover-map inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Decision

On the grouping comparison strip, caption leftover-map axis `k` as
`leftover map comparison axis {k} σ {value}` only when leftoverMapCompareAxisSingular
returns a usable leftover-map singular value from persisted
`leftover_singular_value`. Use the distinct accessible name
`Leftover map comparison axis singular` so the strip caption is not the
leftover-axis report badge (`leftover axis {k} σ {value} {share}%`) and is not
the graphic caption (`leftover-map axis {k} σ {value}`). A missing, non-finite,
or negative leftover-map singular value omits that leftover-map comparison axis
singular badge independently of leftover-map comparison axis share, leftover-map
post coverage notes, leftover-map item coverage notes, leftover-map incomplete
post notes, leftover-map incomplete item notes, leftover pairs, leftover-map
distance `d`, and any leftover-map captions on the pair list and graphic.
Rank-0 leftover-map singular value `0` is shown when that persisted value is a
finite nonnegative number. Do not invent leftover-map singular value from
leftover-map axis share, leftover pair count, plotted marker count, leftover-map
distance, leftover-map rank, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. Do not add the leftover-map graphic to
the strip in this increment. Click a leftover pair on the strip to open that
post.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, the grouping comparison strip names persisted leftover-map
post complete-case coverage, persisted leftover-map item complete-case
coverage, persisted leftover-map incomplete post coverage, persisted
leftover-map incomplete item coverage, persisted leftover-map axis share, and
persisted leftover-map singular values on each grouping row when
leftoverMapCoverageCounts / leftoverMapItemCoverageCounts /
leftoverMapIncompletePostCount / leftoverMapIncompleteItemCount /
leftoverMapCompareAxisShare / leftoverMapCompareAxisSingular return usable
values, then names leftover pairs with leftover-map distance `d`. Closest
and farthest leftover pairs still sit above the member list with the
leftover-map graphic display; click a post marker or a pair button opens that
post.
Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, leftover-map complete-case
coverage on the grouping comparison strip, leftover-map item complete-case
coverage on the grouping comparison strip, leftover-map incomplete post
coverage on the grouping comparison strip, leftover-map incomplete item
coverage on the grouping comparison strip, leftover-map axis share on the
grouping comparison strip, leftover-map inner product, leftover-map cosine,
leftover-map length, leftover-map graphic display, leftover-map axis share
on the graphic display, leftover-map singular values on graphic axes, and
leftover-map singular values on leftover-axis badges.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Leftover-map
singular values are the Gabriel scale `σ_k` of residual SVD axes;
grouping comparison leftover-map singular values name that persisted
`σ_k` for that grouping only when leftoverMapCompareAxisSingular returns
a usable value.)

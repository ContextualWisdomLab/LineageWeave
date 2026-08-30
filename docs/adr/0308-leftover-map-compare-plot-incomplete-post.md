# ADR 0308 — Name leftover-map incomplete post coverage on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map incomplete post coverage on the graphic display
([ADR 0283](0283-leftover-map-plot-incomplete.md)), leftover-map incomplete
post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), leftover-map item
complete-case coverage on the grouping comparison leftover-map graphic
([ADR 0307](0307-leftover-map-compare-plot-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison leftover-map graphic
([ADR 0306](0306-leftover-map-compare-plot-coverage.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map axis share
on the grouping comparison leftover-map graphic
([ADR 0305](0305-leftover-map-compare-plot-axis-share.md)), leftover-map
complete-case coverage persistence
([ADR 0168](0168-leftover-map-complete-case-coverage.md)), leftover pairs on
the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map
coordinates on the compare leftover-pair payload
([ADR 0303](0303-leftover-map-compare-coordinates-payload.md)), leftover-map
coordinates on grouping comparison strip pair rows
([ADR 0302](0302-leftover-map-compare-coordinates.md)), leftover-map
rank on grouping comparison strip pair rows
([ADR 0301](0301-leftover-map-compare-rank.md)), leftover expected on grouping
comparison strip pair rows
([ADR 0300](0300-leftover-map-compare-expected.md)), leftover observed on
grouping comparison strip pair rows
([ADR 0299](0299-leftover-map-compare-observed.md)), leftover residual
on grouping comparison strip pair rows
([ADR 0298](0298-leftover-map-compare-residual.md)), leftover-map unexplained leftover
on grouping comparison strip pair rows
([ADR 0297](0297-leftover-map-compare-unexplained.md)), leftover-map cross share
on grouping comparison strip pair rows
([ADR 0296](0296-leftover-map-compare-cross-share.md)), leftover-map unexplained
leftover share on grouping comparison strip pair rows
([ADR 0295](0295-leftover-map-compare-unexplained-share.md)), leftover-map
explained leftover share on grouping comparison strip pair rows
([ADR 0294](0294-leftover-map-compare-explained-share.md)), leftover-map
reconstruction on grouping comparison strip pair rows
([ADR 0293](0293-leftover-map-compare-reconstruction.md)), leftover-map
incomplete item coverage on the grouping comparison strip
([ADR 0292](0292-leftover-map-compare-incomplete-item.md)), leftover-map item
complete-case coverage on the grouping comparison strip
([ADR 0290](0290-leftover-map-compare-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover
observed `Y` / expected `E` ([ADR 0163](0163-leftover-observed-expected.md)), leftover-map unexplained leftover persistence ([ADR 0182](0182-leftover-map-unexplained.md)),
leftover-map reconstruction persistence
([ADR 0201](0201-leftover-map-reconstruction.md)), leftover-map rank
([ADR 0164](0164-leftover-map-rank.md)), leftover-map rank on pair segments
([ADR 0280](0280-leftover-map-segment-rank.md)), leftover-map coordinate ticks
([ADR 0270](0270-leftover-map-coordinate-ticks.md)), leftover-map graphic display
([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map axis share on
the graphic display ([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map
complete-case coverage on the graphic display
([ADR 0281](0281-leftover-map-plot-coverage.md)), leftover-map item complete-case
coverage on the graphic display
([ADR 0282](0282-leftover-map-plot-item-coverage.md)), and leftover-map coordinates
([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map
post complete-case coverage fail-closed on the pair list
([ADR 0288](0288-leftover-map-list-post-coverage-helper.md)), leftover-map
incomplete item coverage on the pair list
([ADR 0287](0287-leftover-map-list-incomplete-item.md)), leftover-map incomplete
post coverage on the pair list
([ADR 0286](0286-leftover-map-list-incomplete-post.md)), leftover-map item
complete-case coverage on the pair list
([ADR 0285](0285-leftover-map-list-item-coverage.md)), leftover-map incomplete
item coverage on the graphic display
([ADR 0284](0284-leftover-map-plot-incomplete-item.md)), leftover expected on pair
segments ([ADR 0279](0279-leftover-map-segment-expected.md)), leftover observed
on pair segments ([ADR 0278](0278-leftover-map-segment-observed.md)), leftover
residual on pair segments ([ADR 0277](0277-leftover-map-segment-residual.md)),
leftover-map unexplained leftover on pair segments
([ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)), leftover-map
cross share on pair segments ([ADR 0275](0275-leftover-map-segment-cross-share.md)),
leftover-map unexplained leftover share on pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
explained leftover share on pair segments
([ADR 0273](0273-leftover-map-segment-explained-share.md)), leftover-map
reconstruction on pair segments
([ADR 0272](0272-leftover-map-segment-reconstruction.md)), leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map cross share persistence ([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map explained leftover
share persistence ([ADR 0266](0266-leftover-map-explained-share.md)), and leftover-map
incomplete item coverage on the grouping comparison leftover-map graphic.

## Context

ADR 0168 already persists `incomplete_post_count` on
`report_leftover_map_coverage`. ADR 0283 already captions the period-report
leftover-map graphic with `Leftover map dropped N incomplete posts` under
accessible name `Leftover-map graphic incomplete posts`. ADR 0291 already
captions the grouping comparison strip with that same body under accessible
name `Leftover map comparison incomplete posts`. ADR 0304 already draws the
leftover-map graphic of persisted `ξ_{1:2}` / `ζ_{1:2}` above grouping
comparison leftover-pair buttons. ADR 0306 already captions leftover-map
complete-case coverage on that graphic. ADR 0307 already captions leftover-map
item complete-case coverage on that graphic. The comparison graphic still
omits leftover-map incomplete post coverage, so a buyer who reads `used 2 of 3
scored posts (complete-case)` can treat those two markers as the scored-post
census even after the strip note names one dropped post. Incomplete rows are
dropped from Gabriel factorization; hiding the dropped count on the comparison
graphic lets a sparse post with one missing criterion vanish without a next
action.

This increment captions leftover-map incomplete post coverage on the grouping
comparison leftover-map graphic from already-named `leftover_map_coverage`.
Comparison copy uses the accessible name
`Leftover map comparison graphic incomplete posts` so it stays distinct from
hyphen `Leftover-map graphic incomplete posts` on the period-report graphic
and from strip `Leftover map comparison incomplete posts`. It does not add
columns. It does not recompute leftover-map incomplete posts from leftover-map
rank, leftover-map distance, leftover expected, leftover observed, leftover
residual, leftover-map reconstruction, leftover-map unexplained leftover,
leftover-map axis share, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete item coverage, plotted marker count,
leftover pair count, scored minus used, or the count of unused axes. It does
not persist leftover-map inner product, cosine, or length as separate columns.
Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0308** so it does not collide with
leftover-map item complete-case coverage on the grouping comparison leftover-map
graphic (0307), leftover-map complete-case coverage on the grouping comparison
leftover-map graphic (0306), leftover-map axis share on the grouping comparison
leftover-map graphic (0305), leftover-map graphic display on the grouping
comparison strip (0304), leftover-map incomplete post coverage on the graphic
display (0283), leftover-map incomplete post coverage on the grouping comparison
strip (0291), leftover-map graphic display (0268), leftover-map coordinates
(0267), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption persisted leftover-map
incomplete post coverage as `Leftover map dropped N incomplete posts`, using
the same `incomplete_post_count` integer the strip note already shows through
leftoverMapIncompletePostCount. Use the distinct accessible name
`Leftover map comparison graphic incomplete posts` so the graphic caption is
not the strip note (`Leftover map comparison incomplete posts`) and is not the
period-report graphic caption (`Leftover-map graphic incomplete posts`). A
missing coverage row, a negative dropped count, a non-integer dropped count, or
a dropped count that does not equal scored minus used when complete-case
integers are usable omits that leftover-map comparison graphic incomplete posts
caption and keeps leftover-map comparison graphic coverage when leftoverMapCoverageCounts
returns usable complete-case integers, leftover-map comparison graphic item
coverage when leftoverMapItemCoverageCounts returns usable complete-case
integers, leftover map comparison axis share when finite, leftover map
comparison axis text, leftover-map rank when that rank is a non-negative
integer, leftover expected `E` when finite, leftover observed `Y` when finite,
leftover residual `R` when finite, leftover-map unexplained leftover `U` when
finite, leftover-map cross share `x` when finite, leftover-map unexplained leftover
share `s` when finite, leftover-map explained leftover share `e` when finite,
leftover-map reconstruction `R̂` when finite, leftover-map distance `d`, plus
the strip coverage notes. Dropped `0` is shown when that persisted dropped count
is a non-negative integer. Rank-0 origin cells still name incomplete posts when
that dropped count is persisted. Do not invent incomplete posts from scored minus
used, plotted marker count, leftover pair count, leftover-map rank, leftover-map
distance, leftover-map axis share, leftover expected, leftover observed, leftover
residual, leftover-map reconstruction, leftover-map unexplained leftover,
leftover-map post coverage, leftover-map item coverage, leftover-map incomplete
item coverage, or the count of unused axes. Click a post marker to open that post.

Incomplete post coverage omits independently of post coverage and item coverage.
A scored-minus-used mismatch omits leftover-map comparison graphic incomplete
posts and keeps a usable post caption and a usable item caption.

This increment does not caption leftover-map incomplete item coverage on the
comparison graphic. That note already sits on the strip through ADR 0292. A
finite negative leftover on neighbouring fields is shown, never clamped.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
incomplete post coverage on that graphic when leftoverMapIncompletePostCount
returns a usable dropped integer. Rank-0 unused axes still plot at
the origin and still name incomplete posts when that dropped count is persisted.
Click a post marker or a pair button opens that post. Hidden posts stay hidden.
When `Y`, `E`, and `R` are finite, `Y − E = R`. When `R`, `R̂`, and `U`
are finite, `U + R̂ = R`. When `R`, `R̂`, `U`, `x`, `s`, and `e` are
finite, `e + s + x = 1`. When coordinates, reconstruction, and distance
are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover pairs on the grouping comparison
strip, leftover-map complete-case coverage on the grouping comparison strip,
leftover-map item complete-case coverage on the grouping comparison strip,
leftover-map incomplete post coverage on the grouping comparison strip,
leftover-map incomplete item coverage on the grouping comparison strip,
leftover-map reconstruction on grouping comparison strip pair rows,
leftover-map explained leftover share on grouping comparison strip pair rows,
leftover-map unexplained leftover share on grouping comparison strip pair rows,
leftover-map cross share on grouping comparison strip pair rows,
leftover-map unexplained leftover on grouping comparison strip pair rows,
leftover residual on grouping comparison strip pair rows, leftover observed
on grouping comparison strip pair rows, leftover expected on grouping
comparison strip pair rows, leftover-map rank on grouping comparison strip
pair rows, leftover-map coordinates on grouping comparison strip pair rows,
leftover-map coordinates on the compare leftover-pair payload, leftover-map
inner product, leftover-map cosine, leftover-map length, leftover residual
on pair segments, leftover observed on pair segments, leftover expected on
pair segments, leftover-map rank on pair segments, leftover-map unexplained
leftover on pair segments, leftover-map unexplained leftover persistence,
leftover-map cross share on pair segments, leftover-map cross share
persistence, leftover-map unexplained leftover share on pair segments,
leftover-map unexplained leftover share persistence, leftover-map explained
leftover share on pair segments, leftover-map explained leftover share
persistence, leftover-map reconstruction on pair segments, leftover-map
reconstruction persistence, leftover-map item complete-case coverage on the
graphic display, leftover-map item complete-case coverage on the pair list,
leftover-map incomplete post coverage on the graphic display, leftover-map
incomplete post coverage on the pair list, leftover-map incomplete item
coverage on the graphic display, leftover-map incomplete item coverage on
the pair list, leftover-map post complete-case coverage fail-closed on the
pair list, leftover-map rank persistence, leftover-map coordinate
persistence, leftover-map coordinate ticks, leftover-map complete-case
coverage on the graphic display, leftover-map complete-case coverage on the
grouping comparison leftover-map graphic, leftover-map item complete-case
coverage on the grouping comparison leftover-map graphic, leftover-map axis
share on the grouping comparison leftover-map graphic, and leftover-map
incomplete item coverage on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Incomplete rows
are dropped from the complete-case residual rectangle; incomplete post
coverage names how many scored posts stayed out of that factorization.
Grouping comparison leftover-map incomplete post coverage captions that
persisted dropped count on the grouping comparison leftover-map graphic only
when leftoverMapIncompletePostCount returns a usable dropped integer. Rank-0
unused axes still name incomplete posts when that dropped count is stored.)

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

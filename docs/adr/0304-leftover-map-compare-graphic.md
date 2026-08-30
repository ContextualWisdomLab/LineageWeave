# ADR 0304 — Show leftover-map graphic display on grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0305](0305-leftover-map-compare-plot-axis-share.md)
(leftover-map axis share on the grouping comparison leftover-map graphic)

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map
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
([ADR 0292](0292-leftover-map-compare-incomplete-item.md)), leftover-map
incomplete post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), leftover-map item
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
([ADR 0270](0270-leftover-map-coordinate-ticks.md)), and leftover-map coordinates
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
([ADR 0284](0284-leftover-map-plot-incomplete-item.md)), leftover-map incomplete
post coverage on the graphic display
([ADR 0283](0283-leftover-map-plot-incomplete.md)), leftover-map item
complete-case coverage on the graphic display
([ADR 0282](0282-leftover-map-plot-item-coverage.md)), leftover-map complete-case
coverage on the graphic display
([ADR 0281](0281-leftover-map-plot-coverage.md)), leftover expected on pair
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
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map
cross share persistence ([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map explained leftover
share persistence ([ADR 0266](0266-leftover-map-explained-share.md)), and leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0268 already draws the leftover-map graphic display of persisted
Gabriel person coordinates `ξ_{1:2}` and item coordinates `ζ_{1:2}`
above leftover pair buttons on the period-report list. ADR 0303 already
returns those four persisted leftover-map axis columns on
`GET /api/reports/compare/{period}` leftover pairs, and ADR 0302 already
captions `ξ (x, y) ζ (x, y)` on grouping comparison leftover-pair buttons.
The grouping comparison strip still omits the graphic, so a buyer who
compares leftover pairs can treat leftover-map rank, leftover expected `E`,
leftover observed `Y`, leftover residual `R`, leftover-map unexplained leftover
`U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`,
leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`,
leftover-map distance `d`, or the coordinate badge as leftover-map location
without seeing the Gabriel biplot that already names those positions on the
pair list.

This increment reuses LeftoverMapPlot on each grouping comparison row
above leftover-pair buttons when at least one leftover pair has four finite
persisted leftover-map coordinates. It does not add columns. It does not
recompute coordinates from leftover-map rank, leftover-map distance, leftover
expected, leftover observed, leftover residual, leftover-map reconstruction,
leftover-map explained leftover share, leftover-map unexplained leftover share,
leftover-map cross share, leftover-map unexplained leftover, leftover-map
coverage, or the count of unused axes. It does not persist leftover-map inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0304** so it does not collide with
leftover-map coordinates on the compare leftover-pair payload (0303), leftover-map
coordinates on grouping comparison strip pair rows (0302), leftover-map
rank on grouping comparison strip pair rows (0301), leftover
expected on grouping comparison strip pair rows (0300), leftover observed on
grouping comparison strip pair rows (0299), leftover residual on grouping
comparison strip pair rows (0298), leftover-map unexplained leftover on grouping
comparison strip pair rows (0297), leftover-map cross share on grouping
comparison strip pair rows (0296), leftover-map unexplained leftover share on
grouping comparison strip pair rows (0295), leftover-map explained leftover share
on grouping comparison strip pair rows (0294), leftover-map reconstruction on
grouping comparison strip pair rows (0293), leftover-map rank on pair segments
(0280), leftover-map coordinate ticks (0270), leftover-map coordinates (0267),
leftover-map graphic display (0268), leftover expected on pair segments (0279),
leftover observed on pair segments (0278), leftover residual on pair segments
(0277), leftover residual disclosure (0162), leftover observed `Y` / expected `E`
(0163), leftover-map rank persistence (0164), leftover-map reconstruction
persistence (0201), leftover-map coverage on the graphic (0281–0284), leftover-map
axis share on the graphic (0269), or the dashboard stacks.

## Decision

On the grouping comparison strip, render the existing leftover-map graphic
display **above** leftover-pair buttons when at least one leftover pair has
four finite persisted leftover-map coordinates. Person markers are posts at
persisted `ξ_{1:2}`; item markers are criteria at persisted `ζ_{1:2}`. A faint
segment joins each closest or farthest pair so leftover-map distance `d` is
the drawn length, not a second score. The origin stays in view because it is
the rank-0 unused-axis location. Scale is isotropic so Euclidean `d` is
visually comparable on both axes. A rank-0 origin cell plots at `(0, 0)` with
a unit display window; that window is drawing scale, not a leftover score.

Click a post marker to open that post with leftover focus so Post quality
marks the named criterion current (ADR 0158). Criterion markers are not post
buttons. A missing or non-finite coordinate omits that pair from the plot
rather than inventing a location. When no pair has four finite coordinates,
omit the plot and keep the existing leftover-pair buttons, coverage notes, and
coordinate badges. Duplicate posts share one person marker; duplicate criteria
share one item marker.

This increment does not caption leftover-map axis share or leftover-map
coverage on the comparison graphic. Those notes already sit on the strip
through ADR 0289–0292 and stay independent of this plot. Do not invent
coordinates from leftover-map rank, leftover-map distance, leftover expected,
leftover observed, leftover residual, leftover-map reconstruction, leftover-map
unexplained leftover, leftover-map explained leftover share, leftover-map
unexplained leftover share, leftover-map cross share, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, or the count of unused axes. A finite
negative leftover on neighbouring fields is shown, never clamped.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already return
persisted leftover-map coordinates `ξ` / `ζ` also show the leftover-map
graphic display of those already-named positions above leftover-pair buttons
when four finite axes are present. Click a post marker or a pair button opens
that post. Hidden posts stay hidden. When `Y`, `E`, and `R` are finite,
`Y − E = R`. When `R`, `R̂`, and `U` are finite, `U + R̂ = R`. When `R`,
`R̂`, `U`, `x`, `s`, and `e` are finite, `e + s + x = 1`. When coordinates,
reconstruction, and distance are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, leftover-map complete-case
coverage on the grouping comparison strip, leftover-map item complete-case
coverage on the grouping comparison strip, leftover-map incomplete post
coverage on the grouping comparison strip, leftover-map incomplete item
coverage on the grouping comparison strip, leftover-map reconstruction on
grouping comparison strip pair rows, leftover-map explained leftover share
on grouping comparison strip pair rows, leftover-map unexplained leftover
share on grouping comparison strip pair rows, leftover-map cross share on
grouping comparison strip pair rows, leftover-map unexplained leftover on
grouping comparison strip pair rows, leftover residual on grouping
comparison strip pair rows, leftover observed on grouping comparison strip
pair rows, leftover expected on grouping comparison strip pair rows,
leftover-map rank on grouping comparison strip pair rows, leftover-map
coordinates on grouping comparison strip pair rows, leftover-map coordinates
on the compare leftover-pair payload, leftover-map inner product, leftover-map
cosine, leftover-map length, leftover residual on pair segments, leftover
observed on pair segments, leftover expected on pair segments, leftover-map
rank on pair segments, leftover-map unexplained leftover on pair segments,
leftover-map unexplained leftover persistence, leftover-map cross share on
pair segments, leftover-map cross share persistence, leftover-map unexplained
leftover share on pair segments, leftover-map unexplained leftover share
persistence, leftover-map explained leftover share on pair segments,
leftover-map explained leftover share persistence, leftover-map reconstruction
on pair segments, leftover-map reconstruction persistence, leftover-map item
complete-case coverage on the graphic display, leftover-map item complete-case
coverage on the pair list, leftover-map incomplete post coverage on the graphic
display, leftover-map incomplete post coverage on the pair list, leftover-map
incomplete item coverage on the graphic display, leftover-map incomplete item
coverage on the pair list, leftover-map post complete-case coverage fail-closed
on the pair list, leftover-map rank persistence, leftover-map coordinate
persistence, leftover-map coordinate ticks, leftover-map axis share on the
graphic display, leftover-map complete-case coverage on the graphic display,
leftover-map item complete-case coverage on the graphic display, leftover-map
incomplete post coverage on the graphic display, and leftover-map incomplete
item coverage on the graphic display.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Leftover-map
coordinates are persisted Gabriel person `ξ_{1:2}` and item `ζ_{1:2}`
after IRT main effects. Grouping comparison leftover-map graphic display
plots those persisted positions on the grouping comparison strip only when
four stored axes are finite. Rank-0 origin cells still plot at `(0, 0)`
when those axes are stored. When finite, `R̂ = ξ · ζ` and
`d = ‖ξ − ζ‖`.)

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

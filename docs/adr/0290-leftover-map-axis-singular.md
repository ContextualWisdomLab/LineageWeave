# ADR 0290 — Name leftover-map singular values on leftover-axis badges

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover-map axis share persistence
([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
singular values on the graphic display
([ADR 0289](0289-leftover-map-plot-singular.md)), fail-close leftover-map post
complete-case coverage on the pair list
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
([ADR 0281](0281-leftover-map-plot-coverage.md)), leftover-map rank on pair
segments ([ADR 0280](0280-leftover-map-segment-rank.md)), leftover expected on pair
segments ([ADR 0279](0279-leftover-map-segment-expected.md)), leftover observed on
pair segments ([ADR 0278](0278-leftover-map-segment-observed.md)), leftover
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
leftover-map coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)),
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover
observed `Y` / expected `E` ([ADR 0163](0163-leftover-observed-expected.md)),
leftover-map explained leftover share persistence
([ADR 0266](0266-leftover-map-explained-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
leftover-map cross share persistence
([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map unexplained leftover
persistence ([ADR 0182](0182-leftover-map-unexplained.md)), leftover-map rank
persistence ([ADR 0164](0164-leftover-map-rank.md)), leftover-map complete-case
coverage persistence ([ADR 0168](0168-leftover-map-complete-case-coverage.md)),
and leftover-map graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²` and captions leftover-axis report badges with
share only. ADR 0289 already captions leftover-map graphic axes with persisted
`σ_k`. Those leftover-axis badges still hide `σ_k`, so Gabriel (1971)
singular values appear on the plot and never on the report-level leftover-axis
badges that name the same axes. Hiding `σ_k` on the badges lets leftover-map
axis share be read as leftover-map structure even when the buyer cannot tell
whether axis 1 is large because `σ_1` is large or because axis 2 collapsed.

This increment captions leftover-axis report badges with already persisted
leftover-map singular values. It does not add columns. It does not invent
`σ_k` from leftover-map axis share. It does not persist leftover-map inner
product, cosine, or length. It does not land Post quality on the leftover
criterion. Leftover-map distance stays two-axis Euclidean. Do not invent a
leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0290** so it does not collide with
leftover-map singular values on the graphic display (0289), fail-close
leftover-map post complete-case coverage on the pair list (0288), leftover-map
incomplete item coverage on the pair list (0287), leftover-map incomplete post
coverage on the pair list (0286), leftover-map item complete-case coverage on
the pair list (0285), leftover-map incomplete item coverage on the graphic
display (0284), leftover-map incomplete post coverage on the graphic display
(0283), leftover-map item complete-case coverage on the graphic display (0282),
leftover-map complete-case coverage on the graphic display (0281), leftover-map
rank on pair segments (0280), leftover expected on pair segments (0279),
leftover observed on pair segments (0278), leftover residual on pair segments
(0277), leftover-map unexplained leftover on pair segments (0276), leftover-map
cross share on pair segments (0275), leftover-map unexplained leftover share on
pair segments (0274), leftover-map explained leftover share on pair segments
(0273), leftover-map reconstruction on pair segments (0272), leftover-map
distance on pair segments (0271), leftover-map coordinate ticks (0270),
leftover-map axis share on the graphic display (0269), leftover-map graphic
display (0268), leftover-map coordinates (0267 / migration 0245), leftover-map
explained leftover share persistence (0266 / migration 0244), leftover-map
unexplained leftover share persistence (0233 / migration 0233), leftover-map
reconstruction persistence (0201 / migration 0206), leftover-map cross share
(0185), leftover residual disclosure, leftover observed `Y` / expected `E`,
leftover-map rank, two-axis leftover-map distance, leftover coverage,
leftover-map axis share persistence (0148), leftover interaction-map
persistence, occupational construct catalog search (0265), or the dashboard
stacks.

## Decision

On leftover-axis report badges, caption leftover-map axis `k` with persisted
leftover-map singular value `σ_k` when that singular value is finite and
non-negative, including rank-0 zero singular values. Pair-list labels stay
distinct from graphic labels: leftover-axis badges stay
`leftover axis {k} σ {value} {share}%`; leftover-map graphic axes stay
`leftover-map axis {k} σ {value} ({share}%)`. A missing, non-finite, or
negative singular value omits that `σ` badge and keeps the existing
`leftover axis {k} {share}%` text. Do not invent `σ_k` from leftover-map axis
share. Axis 1 and axis 2 stay independently named. Click a leftover pair to
open that post. The grouping comparison strip (ADR 0149) stays on its reduced
leftover payload and does not gain this caption.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-axis report badges name persisted leftover-map
singular values when finite together with persisted leftover-map axis share;
click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name `σ 0.00`. Leftover-map graphic axes (ADR 0289) remain.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share persistence, leftover pairs on the grouping comparison
strip, two-axis leftover-map distance, leftover-map rank, leftover-map
inner product, leftover-map cosine, leftover-map length, leftover-map
reconstruction, leftover-map unexplained leftover, leftover-map cross
share, leftover-map unexplained leftover share, leftover-map explained
leftover share, leftover-map coordinate persistence, leftover-map
graphic display, leftover-map coordinate ticks, leftover-map axis share
on the graphic display, leftover-map complete-case coverage on the graphic
display, leftover-map item complete-case coverage on the graphic display,
leftover-map incomplete post coverage on the graphic display, leftover-map
incomplete item coverage on the graphic display, leftover-map item
complete-case coverage on the pair list, leftover-map incomplete post
coverage on the pair list, leftover-map incomplete item coverage on the
pair list, fail-close leftover-map post complete-case coverage on the
pair list, and leftover-map singular values on the graphic display.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map.)

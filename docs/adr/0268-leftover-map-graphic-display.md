# ADR 0268 — Show leftover-map graphic display of persisted coordinates

**Decision status:** Accepted
**Date:** 2026-08-28

**Amended by:** [ADR 0269](0269-leftover-map-axis-share-plot.md)
(leftover-map axis share on the graphic display);
[ADR 0270](0270-leftover-map-coordinate-ticks.md)
(leftover-map coordinate ticks);
[ADR 0271](0271-leftover-map-segment-distance.md)
(leftover-map distance on pair segments);
[ADR 0272](0272-leftover-map-segment-reconstruction.md)
(leftover-map reconstruction on pair segments)

Amends [ADR 0049](0049-leftover-pair-report-ui.md) and
[ADR 0267](0267-leftover-map-coordinates.md). Independent of leftover-map
explained leftover share ([ADR 0266](0266-leftover-map-explained-share.md)),
leftover-map unexplained leftover share ([ADR 0233](0233-leftover-map-unexplained-share.md)),
and leftover-map reconstruction ([ADR 0201](0201-leftover-map-reconstruction.md)).

## Context

ADR 0267 already persists two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}` on leftover pair rows so
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay
auditable. Those four numbers still read as a badge next to distance.
Gabriel (1971) is a *graphic display* of the same two marker sets;
Jeon et al. (2021) plot the leftover interaction map as person and
item positions after IRT main effects. Hiding the plot lets leftover
residual `R`, leftover-map distance `d`, or reconstruction `R̂` be
read as leftover-map location even after the coordinates themselves
are named.

This increment draws the leftover-map graphic display from already
persisted `ξ` and `ζ`. It does not add columns. It does not persist
leftover-map inner product, cosine, or length (`R̂` and `d` already
are those two-axis facts). It does not land Post quality on the
leftover criterion. Leftover-map distance stays two-axis Euclidean.
Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected increment uses **0268** so it does not
collide with leftover-map coordinates (0267 / migration 0245),
leftover-map explained leftover share (0266 / migration 0244),
leftover-map unexplained leftover share (0233 / migration 0233),
leftover-map reconstruction (0201 / migration 0206), leftover-map
cross share (0185), leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map rank, two-axis leftover-map
distance, leftover coverage, leftover-map axis share (0148), leftover
interaction-map persistence, occupational construct catalog search
(0265), or the dashboard stacks.

## Decision

On each period-report group that already lists leftover pairs, render
a two-axis leftover-map graphic display **above** the leftover pair
buttons when at least one pair has four finite coordinates. Person
markers are posts at persisted `ξ_{1:2}`; item markers are criteria
at persisted `ζ_{1:2}`. A faint segment joins each closest or
farthest pair so leftover-map distance `d` is the drawn length, not a
second score. The origin stays in view because it is the rank-0
unused-axis location. Scale is isotropic so Euclidean `d` is visually
comparable on both axes. A rank-0 origin cell plots at `(0, 0)` with
a unit display window; that window is drawing scale, not a leftover
score.

Click a post marker to open that post with leftover focus so Post
quality marks the named criterion current (ADR 0158). Criterion
markers are not post buttons. A missing or non-finite coordinate omits
that pair from the plot rather than inventing a location. When no
pair has four finite coordinates, omit the plot and keep the existing
pair-list next action. Duplicate posts share one person marker;
duplicate criteria share one item marker. The grouping comparison
strip (ADR 0149) stays on its reduced leftover payload and does not
gain this plot.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the
member list with the leftover-map graphic display of persisted `ξ`
and `ζ`; click a post marker or a pair button opens that post.
Hidden posts stay hidden. Leftover-map axis share captions those
leftover-map axes when finite (ADR 0269). Leftover-map axis ticks name
persisted `ξ` / `ζ` coordinates (ADR 0270). Pair segments name
persisted leftover-map distance `d` (ADR 0271). Pair segments name
persisted leftover-map reconstruction `R̂` (ADR 0272). When coordinates, reconstruction, and
distance are all finite, `R̂ = ξ_{1:2} · ζ_{1:2}` and
`d = ‖ξ_{1:2} − ζ_{1:2}‖` remain the same identities already
persisted by ADR 0267.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map reconstruction,
leftover-map unexplained leftover, leftover-map cross share,
leftover-map unexplained leftover share, leftover-map explained
leftover share, leftover-map coordinate persistence, leftover-map
axis share on the graphic display, and leftover-map coordinate ticks.

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

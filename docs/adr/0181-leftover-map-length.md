# ADR 0181 — Name leftover-map length on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance `d = ‖ξ_p − ζ_i‖` and
leftover residual `R = Y − E[Y|θ, item]` on `report_leftover_pair`.
ADR 0049 already renders closest and farthest pairs above the member
list and opens the named post. Distance is the Jeon et al. (2021,
eq. 3) map gap. Gabriel (1971) also names leftover-map vector lengths
`‖ξ‖` and `‖ζ‖`. Hiding those lengths lets a buyer read a close
leftover-map pair as leftover-map aligned magnitude, or a distant pair
as large leftover-map displacement, without the polar magnitude.

A close leftover-map pair can sit at the origin (`‖ξ‖ = ‖ζ‖ = 0`) or
share a non-origin position (`d = 0` with positive length). Those are
different leftover-map facts.

This increment does not persist leftover-map coordinates, does not name
observed `Y` / expected `E`, does not name leftover-map cosine, does
not name leftover-map inner product, does not name leftover-map rank,
does not split leftover-map distance onto two axes, and does not land
Post quality on the leftover criterion.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0121–0180. This protected-main increment uses **0181** so it does
not collide with leftover-map cosine (0180), leftover-map inner product
(0179), leftover residual disclosure (0178), leftover observed `Y` /
expected `E` (0177), leftover-map rank (0172), two-axis leftover-map
distance (0166), leftover coverage (0168), leftover-map axis share
(0148), or leftover interaction-map persistence (0121).

## Decision

Each leftover pair names `leftover_map_person_length` and
`leftover_map_item_length` — the Euclidean lengths `‖ξ‖` and `‖ζ‖` of
the leftover-map person and item coordinates that produced leftover-map
distance `d`. Migration `0181` is the single source of the columns on
every install path, fresh or existing -- shipped migrations (`0001` /
`0012`) are never edited after the fact. The columns are nullable so
older leftover rows keep distance and residual without fabricating
lengths. Fallback pairs that have no complete-case leftover map omit
the values rather than inventing them. Origin coordinates persist
length `0` because that is the measured leftover-map magnitude.

The pair button shows `‖ξ‖ {person}` and `‖ζ‖ {item}` next to
leftover-map distance `d` when both values are finite. Next action:
leftover-map length names leftover-map magnitude independently of
leftover-map distance; open this post to read the named criterion. A
missing or non-finite length omits the badges and keeps the existing
closest/farthest next action. Do not invent a leftover score. Do not
invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_person_length` and `leftover_map_item_length`. After
`make seed`, closest and farthest leftover pairs sit above the member
list with named `‖ξ‖` and `‖ζ‖` next to `d`; click opens that post.
Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
and leftover-map cosine.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

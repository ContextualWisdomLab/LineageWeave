# ADR 0126 — Leftover-map criterion nodes open the leftover-pair post

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

ADR 0121 persists leftover interaction-map coordinates and renders a
2D Gabriel biplot above leftover pairs. Person (post) nodes are
buttons that open that post. Criterion (item) nodes are diamonds
without a next action: a buyer who sees a highlighted closest or
farthest criterion cannot act on it.

ADR 0125 lands leftover-pair *list* clicks on Post quality with a
leftover-focus flag. This increment is independent of that landing.
The map criterion node opens the leftover-pair post only. It does
not set leftover focus or `aria-current` on Post quality.

A criterion that is not a leftover-pair member has no buyer next
action. Inventing a click that opens an arbitrary post would
fabricate a pair.

## Decision

Export `leftoverPairForCriterion(pairs, criterionCode)`. Prefer the
closest leftover pair for that criterion, then farthest. If none,
the criterion stays a non-interactive diamond.

When a pair exists, the criterion node is `role="button"`, keyboard
activable (Enter / Space), and named `Open leftover map criterion:
{label}`. Activation calls `onSelectPost(pair.post_id)` — the same
handler as a leftover-map person node and leftover-pair list button
on this stack.

Do not pass leftover-focus flags. Hidden posts stay hidden because
the pair's `post_id` is already ABAC-filtered with leftover pairs.

## Consequences

Buyers can click a highlighted leftover-map criterion and read the
post that sat closest (or farthest) from it after IRT main effects.
Non-pair criteria remain visual context on the Gabriel biplot.

## Related

Depends on [ADR 0121](0121-persist-leftover-interaction-map.md),
[ADR 0048](0048-persist-lsirm-leftover-pairs.md), and
[ADR 0049](0049-leftover-pair-report-ui.md). Independent of leftover
criterion evaluation landing.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

# ADR 0149 — Leftover pairs on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

ADR 0048 persists closest and farthest leftover post–criterion pairs.
ADR 0049 shows those pairs above the period-report member list. The
home-page grouping comparison strip (`GET /api/reports/compare/{period}`)
already names mean θ per PU / corp / thread so a buyer can switch
grouping without opening the period-report list first. That strip
does not yet name leftover pairs, so the buyer still has to switch
grouping before they can open a leftover post.

Leftover pairs are already authorized rows. Denormalizing them onto
the comparison strip would invent a second leftover store.

## Decision

The comparison payload carries the same ABAC-filtered `leftover_pairs`
as the period-report payload. Each visible comparison row may name
closest and farthest leftover pairs. Clicking a leftover pair on the
strip opens that post with the same handler as a leftover pair on the
period-report list. A leftover pair for a hidden post is omitted the
same way a hidden member is.

Do not invent leftover numbers or a second theta. Missing leftover
rows render nothing.

## Consequences

After `make seed`, the A-100 comparison row names leftover pairs.
Open a leftover pair from the strip to read the post–criterion cell.
The Period reports member list still shows leftover pairs above
members (ADR 0049). This slice only adds the same authorized leftover
store to the comparison strip.

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

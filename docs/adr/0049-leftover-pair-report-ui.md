# ADR 0049 — Leftover pairs sit above the report member list

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0048 persists closest and farthest leftover post–criterion pairs.
Those pairs only help if a buyer can see them on the Period reports
panel and open the named post without hunting through the member list.

The member list is already the click-through to Event Lineage, Keyman,
and evaluation. Leftover pairs must not replace that list or invent a
second navigation surface.

## Decision

On each period-report group, render leftover pairs **above** the
member list. Each pair is a button: closest or farthest label, post
title, criterion short label, leftover-map distance, and the next
action naming both the post and the Post quality criterion
(“Open {post}, then read Post quality criterion {criterion}.”).
Clicking the button opens that post with `focusCriterionCode` and
lands on `#post-quality-criterion-{code}` (`aria-current`). Leftover
clicks do **not** use the member-row Event Lineage landing, so the
named criterion stays visible.

After `make seed`, closest and farthest leftover pairs sit above the
member list. Click a pair to open that post and read the named
criterion.

Missing leftover rows render nothing — never a placeholder pair.
A hidden post never appears as a leftover pair.

## Consequences

The authorized report payload carries `leftover_pairs` next to
`members` and `selected_items`. Screen-reader names are
`Open leftover closest pair: {title} · {criterion}` and
`Open leftover farthest pair: {title} · {criterion}` so the control
announces the post **and** the criterion, not only the distance.

Figma File ID: `1Su3lDRmiZdcUs47t1QwIX` (ADR 0118 / 0135).

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0003](0003-fast-mlsirm-report-integration.md), and
[ADR 0135](0135-analysis-result-kind-exact-next-actions.md).

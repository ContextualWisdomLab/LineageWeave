# ADR 0158 — Leftover pair click lands Post quality on the named criterion

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

ADR 0049 puts closest and farthest leftover post–criterion pairs above
the period-report member list. Clicking a pair already opens that post.
The reader still has to hunt through Post quality (IRT) for the named
criterion. The leftover residual (Jeon et al., 2021, eq. 3; Gabriel
1971 biplot) is a post–criterion fact, not a post-only fact.

Event Lineage landing (ADR 0078) already shows the pattern: the click
must name the next action and mark the current node. Leftover pairs
must not reuse the Event Lineage `fromReportMember` path. That path
reorders Keyman and evaluation under Event Lineage. A leftover click
is about the IRT leftover criterion, not about reconstructing the DAG.

## Decision

Pass leftover focus with the leftover-pair click: `pair_kind` and
`criterion_code`. Opening the post:

1. Focuses the **Post quality (IRT)** heading.
2. Marks the leftover criterion row `aria-current="true"`.
3. Shows a leftover-criterion next action under that heading:
   “{criterion} is the leftover criterion this post sat closest to /
   farthest from after main effects. Read that Post quality score next.”

The leftover-pair button next action is “Open this post so the leftover
criterion is current in Post quality.” Home-list and report-member opens
do not carry leftover focus, so they do not show leftover copy or mark
a criterion current.

Do not invent leftover scores. Do not persist a second theta. Do not mix
this landing into the leftover interaction-map stack (ADR 0121).

## Consequences

`SelectPostOptions.fromLeftoverPair` is the only leftover-focus carrier.
Evaluation rows already returned by `GET /api/posts/{id}/evaluation`
are sufficient; no new API. Missing leftover rows still render nothing
(ADR 0049). A hidden post still never appears as a leftover pair.

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0049](0049-leftover-pair-report-ui.md), and
[ADR 0003](0003-fast-mlsirm-report-integration.md).
Independent of leftover-map persistence on `feat/persist-lsirm-interaction-map-v2127`.

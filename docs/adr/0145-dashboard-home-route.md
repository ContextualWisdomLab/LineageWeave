# ADR 0145: Dashboard replaces the Board as the `/` landing route

- Status: Accepted
- Date: 2026-08-24

## Context

`/` opened directly onto the Board (`PostList`): a find-and-filter surface,
not a landing page. New and returning readers had no single place to see
which posts and which projects mattered right now. The product brief asks
for a news-portal-style front page ranking "important posts" and "important
projects", explicitly forbidding an invented/hand-tuned weight and naming
[TEPP](https://github.com/ContextualWisdomLab/TEPP) and
[fast-mlsirm](https://github.com/ContextualWisdomLab/fast-mlsirm) (with its
LLM-as-a-Judge step) as the required ranking sources.

This repo already computes exactly that signal. ADR 0003's staged
`fast-mlsirm` integration ships `report_period_score` (a Fixed-Item
Parameter Calibration-linked mean theta) per grouping and period, for a
`GROUPING_KINDS` set that already includes `"project"` alongside
`process_unit`, `corporate_entity`, `thread_group`, and `team` (see
`backend/app/report_ingestion.py`). Each grouping's `report_member_score`
rows carry a per-post `theta_eap` — the same LLM-as-a-Judge-to-IRT pipeline
scored at the individual post level. `GET /api/reports/project` and
`GET /api/reports/project/{period_code}` already serve this, unmodified.

`TEPP` has no live HTTP transport yet (`lineageweave/tepp_client.py`'s
default transport raises `TeppNotAvailable`; see also
[[tepp_readiness_watch]]). ADR 0003 already forbids growing a second
measurement engine to route around that. The Dashboard therefore does not
attempt a TEPP-sourced importance signal — using it would mean either
inventing one or duplicating TEPP's model, both excluded by standing
decisions. This is a fail-closed omission, not a silent one: the honest
state is "not available yet," matching every other TEPP integration point
in this repo.

When no project period report has been calibrated at all (a fresh
deployment before any `rebuild` has run), the post list falls back to the
existing RankWeave fused ranking (`GET /api/rankings`, ADR 0024) — also a
real, paper-grounded fusion of visible-post channels, never an invented
score, just not fast-mlsirm-calibrated.

## Decision

1. Add `Dashboard` (`frontend/src/components/Dashboard.tsx`) as a new
   `WorkspaceDestination`. It calls only existing endpoints — no new backend
   route — reusing `fetchPeriodReportIndex`/`fetchPeriodReports` (grouping
   kind `"project"`) for "Important projects" (sorted by `mean_theta` desc)
   and "Important posts" (each grouping's members deduplicated by post,
   sorted by `theta_eap` desc), and `fetchRankings` as the RankWeave
   fallback when no project theta exists yet.
2. `/` (no `?workspace=` param) now resolves to `"dashboard"` instead of
   `"board"`; the Board stays one click away as the first Workspace nav
   item after Dashboard. Global search and admin board-tool deep links
   still route explicitly to `"board"`, unchanged.
3. Every card's next action is "open this post" — clicking a project card
   opens its highest-theta member post, since no dedicated project detail
   view exists yet; clicking a post card opens that post directly, reusing
   the same `postToOpen`/`changeDestination("board")` hand-off
   `CalendarPanel` and `CustomerMasterPanel` already use.
4. No score renders without stating its source: post/project theta badges
   read `fast-mlsirm θ {value}`; RankWeave-fallback posts read
   `RankWeave fusion`. Empty states name the next action ("Ask an
   administrator to run a period-report rebuild") rather than a bare "no
   data" message.

## Consequences

- No new database objects, migrations, or backend endpoints — this is a
  frontend-only aggregation of two already-shipped, already-tested read
  paths, per Ponytail's reuse-before-build rung.
- The Dashboard is silent about `TEPP` rather than fabricating a temporal
  signal from it; that gap closes only when TEPP ships a live transport
  (tracked in [[tepp_readiness_watch]]), at which point it becomes a third
  ranking input, not a replacement for the fast-mlsirm theta.
- A grouping kind can, in principle, hold zero `"project"` rows if no post
  ever resolved a `secondary_grouping_key` (project mention). The Dashboard
  treats that the same as "not yet calibrated" — RankWeave fallback, honest
  empty-state copy — rather than erroring.
- i18n: all new Dashboard strings ship translated into ko/zh/ja/vi in the
  same PR, consistent with this repo's existing translation discipline.

## Related

Builds on [ADR 0003](0003-fast-mlsirm-report-integration.md) (fast-mlsirm
integration decision and staging), the existing `report_ingestion.py` /
`period_report.py` calibration pipeline, [[tepp_readiness_watch]] (TEPP has
no live transport yet), and ADR 0024 (RankWeave fused post ranking).

## References

Bock, R. D., & Mislevy, R. J. (1982). Adaptive EAP estimation of ability in
a microcomputer environment. *Applied Psychological Measurement, 6*(4),
431–444. https://doi.org/10.1177/014662168200600405

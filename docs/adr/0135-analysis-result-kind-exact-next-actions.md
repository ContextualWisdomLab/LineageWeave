# ADR 0135: Analysis-result next actions stay kind-and-status exact

- Status: Accepted
- Date: 2026-08-23
- Figma: File ID `1Su3lDRmiZdcUs47t1QwIX`
- Related: [0014](0014-authorized-analysis-run-read.md), [0016](0016-analysis-run-knowledge-cutoff-posts.md), [0021](0021-authorized-analysis-run-start.md), [0022](0022-authorized-tepp-start.md), [0025](0025-source-post-revision.md), [0049](0049-leftover-pair-report-ui.md), [0050](0050-seed-period-report-analysis-run.md), [0118](0118-uiux-standard-guide-v3-design-overhaul.md), [0137](0137-cross-post-customer-identity.md)

## Context

The analysis-run list caption is `kind · status · entity`. Next-action copy
on that list and on the opened detail must not mix kinds: a failed lineage
row is not a missing TEPP transport, a failed TEPP row is not a
reconstruction retry, and a failed period report is not a measurement.
A running row whose copy says the work is already queued must not also
offer Start reconstruction / Start TEPP measurement. A succeeded period
report must not say the report is unbuilt. Opening a cutoff-rewritten
title must name both clocks and show **Body this run knew** only when a
revision covers the cutoff.

## Decision

1. Map next-action copy in `analysisRunGuidance` by `run_kind_code` ×
   `status_code`. Tests feed representative run records into that function
   and into `AnalysisRunNextAction` without mocking the panel away.
2. Start is pending lineage or pending TEPP only. Running rows expose
   Refresh this run. Failed TEPP stays terminal (connect transport; do not
   invent a Pending TEPP row). Failed reports with a week key open the
   period-report surface so rebuild is the control that follows rebuild copy.
3. Succeeded report landing still focuses the report period, sets grouping
   to the run's corporate entity when that is the opened run, and places
   the opened-grouping next-action status, mean θ, and member posts ahead
   of other groupings and the week strip.
4. Cutoff live-body warning plus `CutoffKnownBody` remain the comparison
   path. A missing revision is omitted; the live body is never labeled as
   reconstructed evidence without that comparison.
5. Leftover closest/farthest pairs name the post **and** the Post quality
   criterion. Clicking a pair opens that post with `focusCriterionCode` and
   lands on that criterion. It does not reuse the member-row Event Lineage
   landing (ADR 0049).
6. Catalog-unbound, dropped/unavailable channel, and confident-negative
   are three distinct reader states, each with next-action copy. A Null
   channel is dropped and renormalized, never scored as zero. A glued
   job-title + relationship-type phrase stays one source string until a
   reviewed `POST_SUMMARY_CONTRACT_VERSION` bump; do not infer “operates”.

Cross-post customer identity is [ADR 0137](0137-cross-post-customer-identity.md),
not this record. The two decisions previously collided on number 0135.

## Consequences

- Copy and the following control cannot both claim "already queued" and
  "start over".
- Storybook records failed lineage, failed TEPP, failed report, pending
  TEPP, running queued, succeeded-report landing, cutoff live-body
  warning, leftover closest/farthest landing, and catalog-unbound /
  dropped-channel / confident-negative scenes. Each scene has a `play`
  function that clicks or asserts the following control.
- ADR 0013 still forbids storing θ on the analysis-run registry. Mean θ
  on the period-report panel is report evidence, not an invented theta.

## References — APA 7th

World Wide Web Consortium. (2024). *Error suggestion* (Understanding SC
3.3.3). https://www.w3.org/WAI/WCAG22/Understanding/error-suggestion.html

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

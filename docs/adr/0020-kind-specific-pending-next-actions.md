# ADR 0020 — Pending next actions stay kind-specific and audible

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0014 authorized analysis-run read; ADR 0017 authorized
analysis-run create
**Refs:** Merged #128 left pending copy kind-blind; #138 is the same
slice on `main` and must not be duplicated onto this #74 stack

## Context

#128 pinned Failed next-action copy to the registered kinds
(`analysis_run_lineage`, `analysis_run_tepp`, `analysis_run_report`).
Pending rows still used one sentence: "Reconstruction has not started
yet." A Pending TEPP row therefore told the operator to wait for
reconstruction. The list button's `aria-label` also replaced the
visible next-action, so assistive technology only heard the caption
(W3C, 2018, 2023).

#142 owns in-process lineage start. This decision does not start a
run, invent a theta, or add Storybook.

## Decision

- `analysisRunNextAction` switches on both `status_code` and
  `run_kind_code`. Pending TEPP says measurement has not started and
  is not a calibrated result. Pending report says the report has not
  been built. Pending lineage keeps the reconstruction sentence.
- The list button accessible name is
  `Open analysis run: {caption}. {nextAction}` when a next action
  exists, otherwise the caption alone.
- Detail repeats the same next-action sentence after the title so
  opening a Failed or Pending row still tells the operator what to do.
- Running, succeeded, and cancelled rows keep list next-action empty.
  TEPP corpus copy already covers those states on detail.

## Consequences

After `make seed`, open the Failed TEPP row: the list name includes
"connect the measurement service." Request a lineage reconstruction:
the Pending lineage row still says reconstruction has not started.
A Pending TEPP fixture must not say Reconstruction.

## References — APA 7th

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

World Wide Web Consortium. (2023). *Web content accessibility
guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/

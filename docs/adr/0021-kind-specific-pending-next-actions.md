# ADR 0021 — Pending next actions stay kind-specific and audible

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0014 authorized analysis-run read; ADR 0017 authorized
analysis-run create
**Refs:** Merged #148 pinned pending copy to registered kinds. Retention
purge owns ADR 0020. #146 / #149 claimed ADR 0020 and must not land.

## Context

#148 pinned Pending next-action copy to the registered kinds
(`analysis_run_lineage`, `analysis_run_tepp`, `analysis_run_report`).
The list button's `aria-label` still replaced the visible next-action,
so assistive technology only heard the caption (World Wide Web
Consortium, 2018, 2023). A buyer who cannot see the row therefore
cannot hear whether to wait for reconstruction, measurement, or a
period report.

#142 owns in-process lineage start. This decision does not start a
run, invent a theta, or add Storybook.

## Decision

- `analysisRunNextAction` keeps the #148 kind × status pin. Unknown
  wire codes do not echo into the sentence.
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
the Pending lineage detail still says reconstruction has not started.
A Pending TEPP fixture must not say Reconstruction. A Pending
period-report fixture must not say reconstruction or measurement.

## References — APA 7th

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

World Wide Web Consortium. (2023). *Web content accessibility
guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/

# ADR 0022 — Seed records the built period report on the shared snapshot

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0013 normalized analysis-run registry; ADR 0003
fast-mlsirm report integration; ADR 0014 authorized analysis-run read
**Refs:** After `make seed`, lineage and TEPP registry rows were visible
on home Analysis runs, but the calibrated period report lived only on
the separate report panel. ADR 0021 is the person-catalog bind on #153.

## Context

Seed already scores Demo Corp week-2/week-3 reports through
`fast-mlsirm` and persists them on the report tables. The analysis-run
registry already has `analysis_run_report`. Operators who opened
Analysis runs after `make seed` could retry a Failed TEPP transport or
inspect a Succeeded lineage tree, then had no registry row for the
report they could already see on the period-report panel.

A fake Failed report row would contradict the built report. Copying
mean θ onto `analysis_run` would invent a psychometric field the
registry is not allowed to store (ADR 0013).

## Decision

- `_seed_demo_period_report` still builds the calibrated report first.
- `_seed_demo_report_run` then inserts `analysis_run_report` on the
  same Demo Corp snapshot, scoped to the same corporate entity.
- The lifecycle is Pending → Running → Succeeded because the report
  tables already hold the scored period. The run row stores only
  registry digests and counts — never a theta, item bank, or provider
  body.
- Home next-action copy for a Succeeded report stays empty. Failed
  report fixtures still say rebuild the period report.
- `POST /api/analysis-runs` stays lineage-or-TEPP as implemented
  (ADR 0017). This slice does not add a Request period-report button
  and does not call TEPP.

## Consequences

After `make seed`, Demo Analyst opens Analysis runs and sees
**Period report · Succeeded · Demo Corp** next to the lineage and TEPP
rows. Opening it shows the cutoff posts. Mean θ remains on the
period-report panel. Re-seed is idempotent on
`demo-report-seed-2026-w02`.

## References — APA 7th

American Educational Research Association, American Psychological
Association, & National Council on Measurement in Education. (2014).
*Standards for educational and psychological testing*. American
Educational Research Association.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

# ADR 0014 — Analysis-run evidence is an authorized, source-redacting read

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0013 normalized analysis-run registry
**Refs:** Issue #79 (Milestone 2 parent); closed PR #77 is read-only evidence

## Context

PR #89 persists analysis-run identity, aggregate reconciliation, scope,
and lifecycle without exposing a product API. Buyers still cannot see
whether a lineage reconstruction ran, succeeded, or reconciled how many
documents. Closed PR #77 exposed analysis records through a parallel
application that also stored raw metadata payloads -- that shape cannot
become protected product truth.

## Decision

LineageWeave owns a fail-closed read projection of the #89 registry:

- `GET /api/analysis-runs` and `GET /api/analysis-runs/{id}` require
  `post_read`.
- Visibility is evaluated in SQL. A run is visible when the caller
  requested it, or the scope is a corporate entity / process unit /
  thread group the caller may already walk. `all_visible` stays
  requester-only so it cannot broaden another tenant's evidence.
- Hidden runs return 404, not 403, and never appear in the list.
- The payload carries lookup labels and non-negative aggregate counts.
  It does not carry source SQL, DSNs, raw records, image bytes, provider
  payloads, credentials, or another service's table names.
- `GET /api/analysis-runs/{id}` also returns the append-only labeled
  `status_history`. The list does not. A failed event may include the
  stored machine `failure_code`; this slice does not invent a label.
- TEPP remains a versioned `AnalysisRunRequest` consumer
  (`lineageweave.tepp_client`). This slice does not fork TEPP arithmetic.
- contextual-orchestrator remains the only LLM path. This slice does not
  call a raw model API.

## Consequences

`make seed` writes one synthetic Demo Corp lineage run and one TEPP
run on the same snapshot so the existing React home page can show both
kinds without a second application. The TEPP run is Failed /
`tepp_not_available` when the default transport is missing -- the list
keeps that machine code off the caption (this decision) and instead
tells the operator to open the TEPP run, then connect the measurement
service. A failed lineage row tells the operator to retry
reconstruction, not to connect TEPP. A failed period-report row
tells the operator to rebuild the report from a current snapshot.
A pending or running TEPP row must not claim a calibrated
measurement. The detail now shows the legal
lifecycle the registry already stored. `POST /api/analysis-runs` now
records a Pending lineage run on an authorized cutoff capture
(ADR 0017). TEPP and period-report kinds are 422. Reconstruction, a
live TEPP transport, and a fuller Analysis Run Console remain later
slices.

## References

American Educational Research Association, American Psychological
Association, & National Council on Measurement in Education. (2014).
*Standards for educational and psychological testing*. American
Educational Research Association.

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2013/REC-prov-o-20130430/

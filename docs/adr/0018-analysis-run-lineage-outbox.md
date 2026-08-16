# ADR 0018 — Lineage reconstruction is delivered from a PostgreSQL outbox

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0013 normalized analysis-run registry; ADR 0017 authorized
analysis-run create
**Refs:** Issue #79 (Milestone 2 parent); ADR 0013 follow-up 3

## Context

`POST /api/analysis-runs` can record a Pending lineage row (ADR 0017). The
operator could confirm the cutoff corpus, but the row stayed Pending
forever. Reconstructing inside that write would mix request identity with
derivation, and calling `rebuild_lineage` would delete every live
`post_lineage_edge`. TEPP execution remains a later adapter — this slice
must not invent a theta.

## Decision

Migration `0019_analysis_run_outbox.sql` adds two 3NF relations:

- `analysis_run_outbox` — one lineage delivery lease per run (queued,
  leased, completed, failed). A replay cannot enqueue a second worker.
- `analysis_run_lineage_edge` — insert-only parent→child edges for that
  run's cutoff bag. Live `post_lineage_edge` stays the navigation
  projection.

`POST /api/analysis-runs/{id}/reconstruct` claims the outbox, appends
Running, reconstructs the ABAC-visible cutoff posts through ThreadWeave
(`lineage_edge_specs`), persists run-scoped edges, and appends Succeeded
or Failed (`lineage_reconstruction_failed`). Hidden runs 404. TEPP rows
are 422. A Succeeded replay returns the authorized detail.

The home **Request a lineage reconstruction** button reuses one in-flight
idempotency key until the create commits, then starts this delivery.

## Consequences

A buyer can request a run and see reconstructed parent→child links on
that run without wiping the live Event Lineage graph and without a
fabricated measurement. Valkey may later signal the same outbox; PostgreSQL
remains source of truth.

## References — APA 7th

Bernstein, P. A., & Newcomer, E. (2009). *Principles of transaction
processing* (2nd ed.). Morgan Kaufmann.

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns: Designing,
building, and deploying messaging solutions*. Addison-Wesley.

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

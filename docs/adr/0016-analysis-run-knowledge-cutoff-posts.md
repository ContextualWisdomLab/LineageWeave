# ADR 0016 — Analysis-run visible posts honor the run knowledge cutoff

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

ADR 0013 stores `analysis_run.knowledge_cutoff` as the analysis clock:
what that run was allowed to know. The registry trigger already refuses
a cutoff earlier than `analysis_source_snapshot.maximum_available_time`.
The home-page detail, however, listed every ABAC-visible title in the
run's scope from live `source_post` rows. Fixture and seed posts that
defaulted to `created_at = now()` therefore appeared inside a January
2026 run, including a later own-corp follow-up the buyer would treat as
part of that reconstruction.

W3C Time Ontology in OWL (Hobbs & Pan, 2017) and ISO 8601-1:2019 keep
distinct clocks from collapsing. A knowledge cutoff is not "posts the
account can see today."

## Decision

`fetch_visible_scope_posts` filters `created_at <= knowledge_cutoff` on
every scope branch (corporate entity, process unit, thread group, and
all-visible). ABAC visibility is applied after that temporal gate.
Click-through still opens the live post body -- post versioning is a
later slice -- but the run list itself must not advertise a post the
run was not allowed to know. The detail must say that next action
plainly: compare the opened body with this cutoff before treating it
as reconstructed evidence.

Reproducibility digests on the same detail use a labeled group whose
accessible name does not replace the visible prefixes (W3C Accessible
Name and Description Computation 1.1). Full digests stay on `title`
for hover verification and on the API payload; the home list stays
aggregates-only.

Seed and API fixtures backdate in-cutoff posts. A late own-corp private
post remains on the live post list and stays out of the January 2026
run.

## Consequences

- After `make seed`, the Demo Corp lineage run lists Demo public post
  and other in-cutoff Demo Corp titles. The later fixture account-review
  post (2026-02-10) does not appear.
- Open the run, read the live-body warning, then open a listed post
  and compare it with the cutoff date.
- Hover a digest prefix to read the full code or configuration digest
  when you need to match the API payload.
- Post-body versioning at the cutoff remains future work.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

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
run was not allowed to know.

Seed and API fixtures backdate in-cutoff posts. A late own-corp private
post remains on the live post list and stays out of the January 2026
run.

## Consequences

- After `make seed`, the Demo Corp lineage run lists Demo public post
  and other in-cutoff Demo Corp titles. The later fixture account-review
  post (2026-02-10) does not appear.
- Open the run, then open a listed post, to inspect what that cutoff
  actually reconstructed.
- Post-body versioning at the cutoff remains future work.
- Thread-group *run list* visibility now uses the same cutoff
  (ADR 0017). A later public post cannot surface a previously hidden
  thread-group run.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

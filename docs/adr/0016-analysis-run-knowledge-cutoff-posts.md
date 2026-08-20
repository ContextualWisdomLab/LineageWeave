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
Click-through still opens the live post body. Detail compares the live
`updated_at` write clock with `knowledge_cutoff` and marks titles
rewritten after the run. Opening a marked title shows the stored
cutoff-known body (`GET /api/posts/{id}?as_of=`, ADR 0025) beside the
live rewrite. A missing revision is omitted -- never an invented
earlier sentence. The next action is specific: only those marked
titles need a cutoff comparison before treating the live body as
reconstructed evidence.

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
- Open the run: Demo public post is marked updated after cutoff
  (`updated_at` 2026-01-13). Demo private post is not.
- Open a marked title: the popup shows **Body this run knew** from
  `source_post_revision` and the live rewrite. Compare those two texts
  before treating the live body as reconstructed evidence (ADR 0025).
- Hover a digest prefix to read the full code or configuration digest
  when you need to match the API payload.
- Migration 0024 (ADR 0025) stores each rewrite on
  `source_post_revision` so the opened post can show the cutoff-known
  body without putting that body on the analysis-run payload. The write
  clock remains a projection on `source_post.updated_at`.
- Thread-group *run list* visibility now uses the same cutoff
  (ADR 0018). A later public post cannot surface a previously hidden
  thread-group run.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

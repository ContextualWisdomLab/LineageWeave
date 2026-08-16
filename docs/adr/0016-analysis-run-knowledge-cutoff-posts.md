# ADR 0016 — Analysis-run post lists apply the run knowledge cutoff

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0013 normalized analysis-run registry; ADR 0014 authorized analysis-run read
**Refs:** Issue #79 (Milestone 2 parent); PR #89 registry + read projection

## Context

PR #89 stores `knowledge_cutoff` on each `analysis_run` and ADR 0013
requires that a run may use only evidence available at that cutoff.
The v0.82 authorized detail listed every ABAC-visible post in the run
scope. A post written after the cutoff therefore appeared inside a
historical reconstruction. That is the buyer-visible temporal leak:
an operator cannot trust that "this run" is the evidence the run was
allowed to know.

The registry already distinguishes snapshot availability from run
cutoff (Jensen & Snodgrass, 1999; W3C Time Ontology in OWL, 2022).
The read projection must apply the same as-of predicate when it
projects `source_post` titles.

## Decision

`GET /api/analysis-runs/{id}` includes a post title only when:

1. the post is in the run's scope;
2. the caller already has ABAC authority to see that post;
3. `source_post.created_at <= analysis_run.knowledge_cutoff`.

Hidden or later posts never appear. The list payload stays
aggregates-only. `source_counts` remain snapshot inventory
(ADR 0013); the home panel labels them "in the snapshot" so they
are not read as the cutoff-filtered title list. Detail also returns
`code_revision_sha` and `configuration_sha256` so an operator can
confirm the run matches the code and configuration they approved.
Prefixes are shown in the home panel; full digests remain on the API.

The home Analysis runs panel lives in `AnalysisRunsPanel` so the
repeating list/detail object can be inventoried for Storybook without
growing `App.tsx`.

## Consequences

Fixture posts that belong in a January 2026 run must carry a
`created_at` at or before that cutoff. `make seed` stamps Demo public
and Demo private posts at 2026-01-10 and inserts Late Demo public post
at 2026-01-13 as the falsifiable own-corp counter-example. Write/rebuild
APIs, TEPP submission, and run-scoped post bodies remain later slices.

## References

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management.
*IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44.
https://doi.org/10.1109/69.755613

Snodgrass, R. T. (Ed.). (1995). *The TSQL2 temporal query language*.
Springer. https://doi.org/10.1007/978-1-4615-2289-8

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

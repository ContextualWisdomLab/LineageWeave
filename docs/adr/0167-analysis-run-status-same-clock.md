# ADR 0167 — Analysis-run status events share one PostgreSQL write clock

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0013](0013-normalized-analysis-run-registry.md). Independent of
leftover-map persist, leftover UI, leftover two-axis distance, TEPP
arithmetic, and Valkey outbox payload shape.

## Context

ADR 0013 distinguishes lifecycle `occurred_at` from durable
`recorded_at` and requires `occurred_at <= recorded_at`. The 0018
trigger overwrote `recorded_at` with `clock_timestamp()` after a
`FOR UPDATE`. Callers that bound Python `datetime.now(timezone.utc)`
as `occurred_at` reproducibly landed 15–20 ms *after* that write
clock, so `analysis_run_status_time_check` rejected the row
(`CheckViolationError`). Live
`test_start_analysis_run_recovers_the_a100_fork` and
`test_tepp_start_persists_published_accepted_evidence` then could not
Start a Pending lineage or TEPP run against a real PostgreSQL.

The product start path later switched `occurred_at` to
`clock_timestamp()` while still omitting `recorded_at` (DEFAULT plus
trigger). That still leaves a two-clock window: VALUES vs DEFAULT vs
trigger each call `clock_timestamp()` separately, and any remaining
Python-ahead caller (seed, live test helper, or a future bind) fails
the same check.

## Decision

1. Application inserts of `analysis_run_status_event` stamp
   `occurred_at` and `recorded_at` from **one** PostgreSQL
   `clock_timestamp()` (a `SELECT ... FROM (SELECT clock_timestamp()
   AS write_clock)` row). Do not bind Python `datetime.now` as
   occurrence.
2. `enforce_analysis_run_status_transition` still overwrites
   `recorded_at` with database `clock_timestamp()`. If the supplied
   `occurred_at` is already ahead of that clock, raise `recorded_at`
   to `occurred_at` so the check holds. Do not rewrite occurrence:
   monotonicity and "cannot predate the request" stay on the
   caller-supplied instant.
3. Migration 0173 replaces the trigger on databases that already
   applied 0018. The 0018 function body matches so a fresh install
   is the same contract.

Do not invent a leftover score. Do not invent a theta.

## Consequences

Starting a Pending lineage reconstruction or TEPP measurement no
longer fails closed on a 15–20 ms Python-vs-PostgreSQL skew. After
`make seed`, Open the Demo Corp lineage run and Start still recovers
the designed A-100 fork. A synthetic insert whose `occurred_at` is
50 ms ahead of `clock_timestamp()` persists with
`recorded_at >= occurred_at`.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Lebo, T., Sahoo, S., McGuinness, D., Belhajjame, K., Cheney, J.,
Corsar, D., Garijo, D., Soiland-Reyes, S., Zednik, S., & Zhao, J.
(2013). *PROV-O: The PROV ontology* (W3C Recommendation). World Wide
Web Consortium. https://www.w3.org/TR/prov-o/

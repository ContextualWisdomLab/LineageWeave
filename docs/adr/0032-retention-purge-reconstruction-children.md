# ADR 0032 — Granted retention purge empties reconstruction children

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-17
**Depends on:** ADR 0020 granted retention purge; ADR 0021 start reconstruction

## Context

ADR 0020 added `purge_analysis_run_registry` so a run-bearing registry
can empty without a superuser `DISABLE TRIGGER`. ADR 0021 then persisted
immutable `analysis_run_lineage_edge`, `analysis_run_reconstruction`,
and `analysis_source_snapshot_member` rows. After a Demo Corp lineage
reconstruction has started, those children and their delete-reject
triggers would fail-close the published grant + admin + phrase path
(ISO 15489-1:2016 disposition; NIST SP 800-92 protected audit records).

Dirty draft #177 ported this procedure onto a stale 0.87.0-only head.
This decision is the successor on live #74 after v2.10.3. It does not
start reconstruction, invent a theta, expose purge on a public HTTP
route, or grant `analysis_run_retention_admin` to `DATABASE_URL`.

## Decision

`purge_analysis_run_registry` disables user triggers on the three
optional children when `to_regclass` finds them, deletes in this
order, then re-enables the triggers on success and in the exception
handler:

1. `analysis_run_lineage_edge`
2. `analysis_run_reconstruction`
3. migration 0018 registry rows (`analysis_run_status_event`,
   `analysis_run_scope`, `analysis_run`, `analysis_source_count`)
4. `analysis_source_snapshot_member`
5. `analysis_source_snapshot`

A database without those relations still purges. Operators follow the
same unrevoked `analysis_run_retention_grant`,
`GRANT analysis_run_retention_admin`, and
`approved-retention-purge` phrase (ADR 0020). Do not `DISABLE TRIGGER`
as superuser after a Succeeded start.

## Consequences

- After a Demo Corp lineage reconstruction has started, the granted
  retention purge still empties the registry.
- Missing child tables stay a no-op. A 0020-only database still
  purges.
- Purge remains an audited SQL operator action, not a public route.

## References — APA 7th

International Organization for Standardization. (2016). *ISO
15489-1:2016: Information and documentation—Records management—Part 1:
Concepts and principles*.

Kent, K., & Souppaya, M. (2006). *Guide to computer security log
management* (NIST Special Publication 800-92). National Institute of
Standards and Technology. https://doi.org/10.6028/NIST.SP.800-92

PostgreSQL Global Development Group. (2026). *PostgreSQL 18
documentation: 9.29. System information functions and operators*.
https://www.postgresql.org/docs/current/functions-info.html

# ADR 0022 — Granted purge also empties reconstruction evidence

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0020 granted retention purge; ADR 0021 authorized start

## Context

ADR 0020 added `purge_analysis_run_registry` so operators can empty a
run-bearing registry without a superuser `DISABLE TRIGGER`. ADR 0021
then persisted `analysis_run_reconstruction`, `analysis_run_lineage_edge`,
and `analysis_source_snapshot_member`. Those rows reference
`analysis_run` and `analysis_source_snapshot`.

After the first start, the 0020 function hits a foreign-key failure.
The documented operator path (grant + admin + published phrase) no
longer empties the registry. That is not a supported product path
(ISO 15489-1:2016 disposition; NIST SP 800-92 protected audit records).

## Decision

Migration `0023_analysis_run_retention_purge_reconstruction.sql`
replaces `purge_analysis_run_registry` so that, after the same
conjunctive authorization, it:

1. disables reconstruction and snapshot-member immutability triggers
   when those tables exist;
2. deletes `analysis_run_lineage_edge` then `analysis_run_reconstruction`;
3. deletes the 0018 registry rows;
4. deletes `analysis_source_snapshot_member`;
5. deletes `analysis_source_snapshot`;
6. re-enables every trigger it disabled;
7. writes one `analysis_run_retention_event`.

Authorization, `REVOKE ALL … FROM PUBLIC`, and the published phrase
do not change. Rollback 0023 restores the 0020 function body.

## Consequences

Operators who started a Pending lineage run can still empty the
registry through the documented grant path, then roll back 0023, 0022,
0021, 0020, and 0018. A raw `DELETE` of reconstruction rows stays
rejected. Do not expose purge on a public HTTP route.

## References — APA 7th

International Organization for Standardization. (2016). *ISO 15489-1:2016:
Information and documentation—Records management—Part 1: Concepts and
principles*.

Kent, K., & Souppaya, M. (2006). *Guide to computer security log management*
(NIST Special Publication 800-92). National Institute of Standards and
Technology. https://doi.org/10.6028/NIST.SP.800-92

National Institute of Standards and Technology. (2020). *Security and
privacy controls for information systems and organizations* (NIST Special
Publication 800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
5.8. Privileges*.
https://www.postgresql.org/docs/current/ddl-priv.html

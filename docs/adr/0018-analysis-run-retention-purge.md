# ADR 0018 — Approved retention purge empties an immutable analysis-run registry

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0013 normalized analysis-run registry

## Context

ADR 0013 and migration `0018` make `analysis_run`, `analysis_run_scope`, and
`analysis_run_status_event` immutable. The 0018 rollback refuses to drop
non-empty registry relations and tells operators to export or delete evidence
under an approved retention procedure.

After the first `analysis_run` insert, a raw `DELETE` is rejected. Snapshot
delete is then blocked by the foreign key. Operators following the documented
procedure cannot satisfy `analysis_run_registry_not_empty` without a superuser
`DISABLE TRIGGER`. That is not a supported product path (ISO 15489-1:2016
disposition; NIST SP 800-92 protected audit records).

## Decision

Migration `0019_analysis_run_retention_purge.sql` adds:

- `purge_analysis_run_registry(approval_token text)` — `SECURITY DEFINER`,
  accepts only `approved-retention-purge`, disables the three immutability
  delete triggers inside that call, deletes in FK order, re-enables the
  triggers, and writes one `analysis_run_retention_event`;
- `analysis_run_retention_event` — purged run/snapshot counts and the SHA-256
  of the approval token. The raw phrase is never stored.

A session `SET` cannot authorize a raw `DELETE`. After purge, export the
retention event, delete those rows, roll back 0019, then roll back 0018.

## Consequences

- A run-bearing registry can be emptied without superuser trigger disable.
- Retention remains an explicit, audited operator action, not a silent
  downgrade.
- 0018 rollback stays fail-closed until the registry tables are empty.

## Follow-up

Bind the approval token to an authenticated administrator grant table when
the write API exists. Do not expose purge on a public HTTP route.

## References — APA 7th

International Organization for Standardization. (2016). *ISO 15489-1:2016:
Information and documentation—Records management—Part 1: Concepts and
principles*.

Kent, K., & Souppaya, M. (2006). *Guide to computer security log management*
(NIST Special Publication 800-92). National Institute of Standards and
Technology. https://doi.org/10.6028/NIST.SP.800-92

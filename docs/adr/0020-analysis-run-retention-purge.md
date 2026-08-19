# ADR 0020 — Approved retention purge requires a session grant and admin role

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

A `SECURITY DEFINER` function that `PUBLIC` can execute, or that accepts only
a documented phrase, lets any SQL session wipe analysis-run evidence
(NIST SP 800-53 Rev. 5 AC-3; CWE-250). The phrase is a procedure name, not
an authorization secret. The write API is a separate slice; SQL operators
still need a grant that is independent of application `user_account` rows.

Landed #122 occupies ADR 0018 / package 0.86.0 for the team and organization
related-node walk. ADR 0019 binds `cataloged_team_id` /
`cataloged_corporate_entity_id` on `post_summary_role` and must not be
reused here. This decision is the next free slot.

## Decision

Migration `0020_analysis_run_retention_purge.sql` adds a conjunctive
fail-closed purge:

- `analysis_run_retention_grant` — one unrevoked row per
  `database_role_name`; history of revoked grants is allowed;
- `analysis_run_retention_admin` — `NOLOGIN` role that receives
  `EXECUTE`; `PUBLIC` does not;
- `purge_analysis_run_registry(approval_token text)` — `SECURITY DEFINER`,
  checks the unrevoked grant, then `pg_has_role(..., 'member')` on the
  admin role, then accepts only `approved-retention-purge`, disables the
  three immutability delete triggers inside that call, deletes in FK
  order, re-enables the triggers, and writes one
  `analysis_run_retention_event`;
- `analysis_run_retention_event` — purged run/snapshot counts, the SHA-256
  of the approval token, `invoking_session_role`, `invoking_current_role`,
  and optional `client_network_address`. The raw phrase is never stored.

A session `SET` cannot authorize a raw `DELETE`. A table-DML runtime role
that only knows the public phrase cannot call the function. A member of
the admin role without a grant cannot purge. A grant without admin
membership cannot purge. After purge, export the retention event, delete
those rows, roll back 0020, then roll back 0018.

This migration does not insert a grant or grant the admin role to the
migrator. Production `DATABASE_URL` must not be a superuser and must not
hold either privilege.

## Consequences

- A run-bearing registry can be emptied without superuser trigger disable.
- Retention remains an explicit, audited operator action, not a silent
  downgrade.
- 0018 rollback stays fail-closed until the registry tables are empty;
  0020 rollback stays fail-closed until retention events are exported
  and deleted.
- Repeated citation-chip and close-button appearance lives in
  `frontend/src/styles/tokens.css` and the Storybook inventory.

## Follow-up

When the authorized write API exists, bind an administrator
`user_account` to the same grant table. Keep the SQL-role grant for
operators who purge from `psql`. Do not expose purge on a public HTTP
route. Split the application login from the migration owner so the
product role cannot execute the function even as table owner.

Start reconstruction (ADR 0021) adds `analysis_run_lineage_edge`,
`analysis_run_reconstruction`, and `analysis_source_snapshot_member`
with delete-reject triggers. This procedure already disables those
user triggers when `to_regclass` finds the tables, deletes lineage
edges, then reconstruction, then the 0018 rows, then snapshot
members, then the snapshot, and re-enables the triggers (ADR 0032).
A 0020-only database without those relations still purges. Do not
require a superuser `DISABLE TRIGGER` after a Succeeded start.

## References — APA 7th

American Institute of Certified Public Accountants. (2017). *SOC 2®: SOC
for Service Organizations: Trust Services Criteria*.

International Organization for Standardization. (2016). *ISO 15489-1:2016:
Information and documentation—Records management—Part 1: Concepts and
principles*.

Kent, K., & Souppaya, M. (2006). *Guide to computer security log management*
(NIST Special Publication 800-92). National Institute of Standards and
Technology. https://doi.org/10.6028/NIST.SP.800-92

MITRE. (2026). *CWE-250: Execution with unnecessary privileges*.
https://cwe.mitre.org/data/definitions/250.html

National Institute of Standards and Technology. (2020). *Security and
privacy controls for information systems and organizations* (NIST Special
Publication 800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
5.8. Privileges*.
https://www.postgresql.org/docs/current/ddl-priv.html

# ADR 0019 — Retention purge requires an unrevoked database-role grant

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0018 approved retention purge

## Context

ADR 0018 publishes `purge_analysis_run_registry('approved-retention-purge')`
as the only supported way to empty a run-bearing registry. The approval
phrase is documentation, not a secret. A `SECURITY DEFINER` function that
`PUBLIC` can execute therefore lets any SQL session wipe analysis-run
evidence (NIST SP 800-53 Rev. 5 AC-3; CWE-250). The retention event also
omitted the caller, so a compliance officer cannot answer who purged
(NIST SP 800-53 Rev. 5 AU-3; NIST SP 800-92).

The write API is a separate slice. SQL operators still need a grant that
is independent of application `user_account` rows.

## Decision

Migration `0019_analysis_run_retention_purge.sql` (this successor) adds:

- `analysis_run_retention_grant` — one unrevoked row per
  `database_role_name`; history of revoked grants is allowed;
- a grant check on `session_user` before the token check
  (`analysis_run_retention_not_granted`);
- `invoking_session_role` on `analysis_run_retention_event` — the
  caller's `session_user`, never the `SECURITY DEFINER` owner;
- `REVOKE ALL ON FUNCTION purge_analysis_run_registry(text) FROM PUBLIC`.

The migrator's `session_user` receives the first grant so `make seed`
and the live contract tests keep working. Insert another grant before
delegating purge to a second operator role. Do not expose purge on a
public HTTP route.

## Consequences

- A published token without a grant cannot empty the registry.
- The exportable retention event names the database role that purged.
- 0018 rollback stays fail-closed until registry tables are empty;
  0019 rollback stays fail-closed until retention events are exported
  and deleted.

## Follow-up

When the authorized write API exists, bind an administrator
`user_account` to the same grant table. Keep the SQL-role grant for
operators who purge from `psql`.

## References — APA 7th

Joint Task Force. (2020). *Security and privacy controls for information
systems and organizations* (NIST Special Publication 800-53, Rev. 5).
National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-53r5

Kent, K., & Souppaya, M. (2006). *Guide to computer security log
management* (NIST Special Publication 800-92). National Institute of
Standards and Technology. https://doi.org/10.6028/NIST.SP.800-92

MITRE. (2026). *CWE-250: Execution with unnecessary privileges*.
https://cwe.mitre.org/data/definitions/250.html

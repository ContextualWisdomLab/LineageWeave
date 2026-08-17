# CLAUDE.md

Tool-specific pointer. Policy lives in [AGENTS.md](AGENTS.md) and the
ADRs under `docs/adr/`. Do not fork those rules here.

## Analysis-run retention (v0.87.0)

To empty a run-bearing registry, insert an unrevoked
`analysis_run_retention_grant` for `session_user` and
`GRANT analysis_run_retention_admin` (ADR 0020). Then
`select purge_analysis_run_registry('approved-retention-purge')`,
export `analysis_run_retention_event`, delete those rows, and roll
back 0020 then 0018. The published phrase is not a secret. Do not
`DISABLE TRIGGER` as superuser. Do not grant the admin role or a
retention grant to the application `DATABASE_URL` login. ADR 0019
is the R&R catalog-id bind, not this purge.

## Analysis-run seed (v0.96.0)

`make seed` writes a Demo Corp lineage run, a TEPP run, and a Succeeded
period-report run on the same snapshot (ADR 0013 / ADR 0024). The TEPP path goes through `tepp_client`. A missing
transport or an unused accepted envelope is Failed
(`tepp_not_available` / `tepp_result_not_persisted`). Do not invent a
theta or a local psychometric substitute. The home list caption stays
`kind · status · entity`; the machine failure code is detail-only
(ADR 0014). Open a Failed TEPP row, then connect a live TEPP
transport. A failed lineage row retries reconstruction -- it does not
mention TEPP. A failed period-report row rebuilds the report. A
pending TEPP row does not claim a calibrated measurement. A pending
lineage row says reconstruction has not started yet.
Digest prefixes stay audible; hover a prefix to read the full digest.
Opening a cutoff title shows the live post. Titles marked updated
after cutoff were rewritten after the run; compare those bodies
before treating them as reconstructed evidence (ADR 0016).
`POST /api/analysis-runs` records Pending on an authorized
cutoff capture (ADR 0017). `POST /api/analysis-runs/{id}/start`
commits Running plus a durable outbox row, then reconstructs that
frozen cutoff bag (ADR 0021 / ADR 0023) or submits TEPP through
`tepp_client` (ADR 0022). A missing transport or unused accepted
envelope is Failed. Failed TEPP is terminal — request a new run,
then start. Do not invent a theta. Hover the Result prefix to read
the parent-choice digest.
After `make seed`, open **Period report · Succeeded · Demo Corp**,
then **Open period report 2026-W02**. The home week is already
2026-W02, so the grouping comparison strip lands on Demo Corp. Report
grouping is Corporate entity and Demo Corp is current. Changing the
week first still focuses the report period field. Mean θ stays on the
period-report panel.

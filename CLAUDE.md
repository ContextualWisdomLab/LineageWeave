# CLAUDE.md

Tool-specific pointer. Policy lives in [AGENTS.md](AGENTS.md) and the
ADRs under `docs/adr/`. Do not fork those rules here.

## Analysis-run retention (v0.87.0)

To empty a run-bearing registry, insert an unrevoked
`analysis_run_retention_grant` for `session_user` and
`GRANT analysis_run_retention_admin` (ADR 0020). Then
`select purge_analysis_run_registry('approved-retention-purge')`,
export `analysis_run_retention_event`, delete those rows, and roll
back 0020 then 0018. The same call empties reconstruction children
when ADR 0021 tables exist (ADR 0032). The published phrase is not a
secret. Do not `DISABLE TRIGGER` as superuser. Do not grant the admin
role or a retention grant to the application `DATABASE_URL` login.
ADR 0019 is the R&R catalog-id bind, not this purge. Person catalog
identity on that role row is ADR 0027 (`cataloged_person_id`).

## Analysis-run seed (v0.96.0)

`make seed` writes a Demo Corp lineage run, a Failed missing-transport
TEPP run, a Failed accepted-evidence TEPP run, and a Succeeded
period-report run on the same snapshot (ADR 0013 / ADR 0024 / ADR 0035).
The TEPP path goes through `tepp_client`. A missing transport or an
unpublished envelope is Failed (`tepp_not_available` /
`tepp_result_not_persisted`). A published accepted acknowledgement is
Failed (`tepp_completed_result_unsupported`) and is shown as aggregate
transport evidence. Do not stamp Succeeded from that ack. Do not invent
a theta or a local psychometric substitute. Measurement evidence shows
Received, and recorded only when that row-write instant differs.
The home list caption stays `kind · status · entity`; the machine
failure code is detail-only (ADR 0014). Open a Failed TEPP row, then
connect a live TEPP transport or read aggregate transport evidence.
Do not treat that row as a validated multilevel estimate. A failed lineage row retries reconstruction -- it does not
mention TEPP. A failed period-report row rebuilds the report. A
pending TEPP row does not claim a calibrated measurement and does
not say reconstruction. The list button name includes the
next-action sentence. A pending lineage row says reconstruction has
not started yet.
Digest prefixes stay audible; hover a prefix to read the full digest.
Opening a cutoff title shows the live post. Titles marked updated
after cutoff were rewritten after the run; the opened body names
both clocks and shows **Body this run knew** beside the live
rewrite. Compare those two texts before treating the live body as
reconstructed evidence (ADR 0016 / 0025).
The January 12 Demo Corp lineage and TEPP runs list Demo public post
and do not list Late Demo public post (2026-01-13). The live post
list still shows Late Demo.
`POST /api/analysis-runs` records Pending lineage only on an
authorized cutoff capture (ADR 0017). TEPP and period-report kinds
are 422. The Request button waits until affiliated corps load; choose
a corp if the token walks more than one. `POST /api/analysis-runs/{id}/start`
commits Running plus a durable outbox row, then reconstructs that
frozen cutoff bag (ADR 0021 / ADR 0023) or submits TEPP through
`tepp_client` (ADR 0022 / ADR 0035). Status `recorded_at` is
`greatest(clock_timestamp(), occurred_at)` so a Python-ahead
occurrence does not fail the write-clock check (ADR 0013 / v2.12.6).
A missing transport or unpublished
envelope is Failed. A published accepted acknowledgement is Failed
transport evidence, not a completed measurement. Failed TEPP is
terminal — connect a TEPP transport from that Failed row or read the
stored evidence. Create does not invent a Pending
TEPP row. Do not invent a theta. Hover the Result prefix to read
the parent-choice digest.
After `make seed`, open **Period report · Succeeded · Demo Corp**,
then **Open period report 2026-W02**. The home week is already
2026-W02, so the grouping comparison strip lands on Demo Corp. Report
grouping is Corporate entity and Demo Corp is current. The focused
chip name contains `Corporate entity: Demo Corp` and the persisted
mean θ. The period-report panel says Demo Corp is the opened grouping
and to read its mean θ and member posts, then open a post. Those
members land immediately under that next action, ahead of Other Corp
and the week strip. Opening Public post names the next action: read
Event Lineage, Keyman, and evaluation on that post. The popup Event
Lineage DAG marks that post current. After that current node, the
popup names Keyman and evaluation as the next read. After landed
evaluation, the popup names the first Keyman as the next read. After
landed Ada West related, the popup names the first related node as
the next read. After that next action, the popup lands Priya Nair
related nodes. After those related nodes land, the popup names Ask
about this lineage as the next read. After that next action, the
popup lands Ask about this lineage. After landed chat, the popup names
the first Ask. After that next action, the popup lands the first Ask
answer. After landed first Ask answer, the popup names the first
cited source. After that next action, the popup lands the first cited
evidence. Changing the week first still
focuses the report period field. Mean θ stays on the period-report
panel.
A listed analysis-run that then 404s stays generic: do not name the
thread or the cutoff. After that 404, re-read the authorized list so
the stale row does not stay clickable. Announce the next action with
`role="alert"` without moving focus.

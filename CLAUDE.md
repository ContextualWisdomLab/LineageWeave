# CLAUDE.md

Tool-specific pointer. Policy lives in [AGENTS.md](AGENTS.md) and the
ADRs under `docs/adr/`. Do not fork those rules here. The sections below
are only the operational details Claude is asked for most often; every
rule they reference is stated once in AGENTS.md with its ADR.

## Analysis-run retention purge (ADR 0020)

To empty a run-bearing registry, insert an unrevoked
`analysis_run_retention_grant` for `session_user` and
`GRANT analysis_run_retention_admin`, then
`select purge_analysis_run_registry('approved-retention-purge')`,
export `analysis_run_retention_event`, delete those rows, and roll
back 0020 then 0018. The published phrase is not a secret. Do not
`DISABLE TRIGGER` as superuser. Do not grant the admin role or a
retention grant to the application `DATABASE_URL` login. ADR 0019
is the R&R catalog-id bind, not this purge; person catalog identity
on that role row is ADR 0027 (`cataloged_person_id`). Purge never
sits on a public HTTP route.

## Analysis-run seed and run states (ADR 0013 / 0014 / 0024)

`make seed` writes a Demo Corp lineage run, a TEPP run, and a Succeeded
period-report run on one snapshot. The TEPP path goes through
`tepp_client`: a missing transport or an unused accepted envelope is
Failed (`tepp_not_available` / `tepp_result_not_persisted`). Never
invent a theta or a local psychometric substitute.

- Failed TEPP is terminal -- open that row and connect a live TEPP
  transport from it.
- A failed lineage row retries reconstruction and does not mention TEPP;
  a failed period-report row rebuilds the report.
- Pending rows claim nothing: pending TEPP is not a calibrated
  measurement, pending lineage has not started reconstructing yet.
- Home list captions stay `kind · status · entity`; machine failure
  codes are detail-only (ADR 0014).

## Cutoff knowledge (ADR 0016 / 0025)

Opening a cutoff-rewritten title shows **Body this run knew** from
`source_post_revision` beside the live rewrite, with both clocks named.
Compare those two texts before treating the live body as reconstructed
evidence; do not invent an earlier sentence when no revision covers the
cutoff.

## Where the rest lives

Create/start endpoint rules (ADR 0017 / 0021), tie-vs-miss similarity
(ADR 0026), R&R catalog ids (ADR 0019 / 0027), leftover pairs
(ADR 0048–0164 / 0182), the text-channel embedding swap and cosine
clamp (ADR 0190), per-edge channel-score persistence (ADR 0195),
migration replay (ADR 0166), docstring coverage, and the measurement
boundary are all stated in [AGENTS.md](AGENTS.md) -- read it before
changing code, tests, or runtime policy rather than restating anything
here.
=======
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
after cutoff were rewritten after the run; the opened body names
both clocks and shows **Body this run knew** beside the live
rewrite. Compare those two texts before treating the live body as
reconstructed evidence (ADR 0016 / 0025).
`POST /api/analysis-runs` records Pending lineage only on an
authorized cutoff capture (ADR 0017). TEPP and period-report kinds
are 422. The Request button waits until affiliated corps load; choose
a corp if the token walks more than one. `POST /api/analysis-runs/{id}/start`
commits Running plus a durable outbox row, then reconstructs that
frozen cutoff bag (ADR 0021 / ADR 0023) or submits TEPP through
`tepp_client` (ADR 0022). A missing transport or unused accepted
envelope is Failed. Failed TEPP is terminal — connect a TEPP
transport from that Failed row. Create does not invent a Pending
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
and the week strip. After `make seed`, leftover closest/farthest pairs
sit above the member list with leftover-map rank (rank 0 names no
leftover structure) and unexplained leftover `U` next to leftover-map
distance `d`. Leftover-map axis share badges name Gabriel inertia
of axes 1 and 2; open a leftover pair to read the post–criterion cell.
The shares do not invent a leftover score. Global Ask Event Lineage for
cited posts comes from one post/edge fetch pair and names truncation
when the merged graph hits the landing bound (ADR 0169). Opening Public
post names the next action: read
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

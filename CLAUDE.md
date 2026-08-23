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
is the R&R catalog-id bind, not this purge. Person catalog identity
on that role row is ADR 0027 (`cataloged_person_id`).

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

## Weekly VOC (v2.12.0 / v2.13.0)

On Board, click **Weekly VOC**. Voice of Customer posts for the latest
ISO-8601 week stay; other VOC types and older weeks drop out. The Board
names Event Lineage as the next read (ADR 0092). Open a remaining post:
Event Lineage takes focus and names Keyman and evaluation next
(ADR 0093). A home-list open does not. Do not invent a theta.

## Calendar open (v2.14.0)

Open Calendar. Authorized commitments are current. Open a commitment:
Event Lineage takes focus and names Keyman and evaluation next
(ADR 0094). A home-list open does not. Do not invent a theta or a
CalDAV event.

## Customer master open (v2.15.0)

Open Customer master. Authorized customer entities are current. Open a
related post: Event Lineage takes focus and names Keyman and evaluation
next (ADR 0095). A home-list open does not. Do not invent a theta or a
customer.

## Ask Agent open (v2.16.0)

Open Ask Agent. After an authorized answer, cited posts are current. Open
a cited post: Event Lineage takes focus and names Keyman and evaluation
next (ADR 0096). A home-list open does not. Do not invent a theta or a
cited post.

## Event Lineage DAG walk (v2.17.0)

From a GNB-focused popup, open a linked Event Lineage node: Event Lineage
stays focused and names the new post as current (ADR 0097). A home-list
DAG walk does not. Do not invent a theta.

## Ask Agent knowledge cutoff (v2.23.0)

Open Ask Agent. Optionally set a knowledge cutoff. A dated question uses
retained source-post revisions from that clock. A live query stays
live-only and is never labeled as-of. A missing historical body is named
and the live rewrite is not used (ADR 0135). Do not invent a theta or a
cutoff body.

## GNB Event Lineage focuses Keyman (v2.19.0)

A GNB-origin popup (Weekly VOC, Calendar, Customer master, Ask Agent, or a
linked Event Lineage DAG walk from one of those) keeps Event Lineage
current and moves focus to the Keyman heading once Keyman rows have
settled (ADR 0100). The report-member auto-land chain to related nodes
and Ask is not used for GNB origins. A home-list open does not gain that
 focus. Do not invent a theta.

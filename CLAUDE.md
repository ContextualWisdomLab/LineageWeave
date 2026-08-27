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
cutoff. Global Ask optional `knowledge_cutoff` uses the same cover
(ADR 0216).

## Where the rest lives

Create/start endpoint rules (ADR 0017 / 0021), tie-vs-miss similarity
(ADR 0026), R&R catalog ids (ADR 0019 / 0027), leftover pairs
(ADR 0048–0164 / 0182 / 0185 / 0201 / 0233), occupational construct catalog search
(ADR 0257), the text-channel embedding swap and cosine
clamp (ADR 0190), per-edge channel-score persistence (ADR 0195),
token-backed status notices (ADR 0220),
migration replay (ADR 0166), docstring coverage, and the measurement
boundary are all stated in [AGENTS.md](AGENTS.md) -- read it before
changing code, tests, or runtime policy rather than restating anything
here.

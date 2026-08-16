# CLAUDE.md

Tool-specific pointer. Policy lives in [AGENTS.md](AGENTS.md) and the
ADRs under `docs/adr/`. Do not fork those rules here.

## Analysis-run seed (v0.85.0)

`make seed` writes a Demo Corp lineage run and a TEPP run on the same
snapshot (ADR 0013). The TEPP path goes through `tepp_client`. A missing
transport or an unused accepted envelope is Failed
(`tepp_not_available` / `tepp_result_not_persisted`). Do not invent a
theta or a local psychometric substitute. The home list caption stays
`kind · status · entity`; the machine failure code is detail-only
(ADR 0014). Open a Failed TEPP row, then connect a live TEPP
transport. A failed lineage row retries reconstruction -- it does not
mention TEPP.
Digest prefixes stay audible; hover a prefix to read the full digest.
Opening a cutoff title shows the live post -- compare it with the
cutoff before treating the body as reconstructed evidence (ADR 0016).
`POST /api/analysis-runs` records Pending on an authorized
cutoff capture (ADR 0017) and does not reconstruct lineage.

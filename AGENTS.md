# AGENTS.md

Cross-agent conventions for `LineageWeave`, readable by any coding agent
(Claude, Codex, Cursor, opencode, ...). Keep this file tool-agnostic.

## What this repo is

A demo BI prototype that reconstructs git-branch-style lineage between
scattered short records. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
design and [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md)
for the literature it is grounded in.

## Hard rule: no real data, ever

This repo ships **synthetic data only** (`lineageweave/fixtures.py`) and
must never reference, by name or otherwise identifiably, any real
organization whose data motivated this design. Never add a fixture, test
case, screenshot, or example derived from a real organization's records. If you are extending this repo to validate against
real data, do that validation entirely outside this repository (a private
scratch script against a local database is fine) and only bring back
**aggregate, non-identifying findings** -- see how
`docs/lineage-bi-research-notes.md`'s "2.6%" validation number is phrased:
a statistic, never a title, name, or id.

## Reuse before you build

This repo depends on real ContextualWisdomLab-org packages rather than
reimplementing them:

- [ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave) for
  tree assembly (`reconstruct.py`'s `_walk`/`thread_messages` calls).
- [RankWeave](https://github.com/ContextualWisdomLab/RankWeave) for
  multi-channel score fusion (`weighted_convex_fuse`).
- [TEPP](https://github.com/ContextualWisdomLab/TEPP)'s published wire
  contract for calibrated measurement (`tepp_client.py`) -- never
  reimplement TEPP's model here.
- [contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
  for LLM adjudication (`adjudication_client.py`) -- never call a raw LLM
  API directly from this repo; go through the orchestrator so
  reasoning-effort allocation and cost attribution stay centralized.

Before adding a new dependency, check whether an existing org repo already
does it (`gh repo list ContextualWisdomLab`).

## Pluggable channels: never fake a missing signal

`NullEmbeddingClient`, `NullAdjudicationClient`,
`NullKeymanExtractionClient`, `NullEntityRelationshipClient`,
`NullPostSummaryClient`, `NullPostChatClient`, and
`NullCommitmentExtractionClient` (and any new channel client you add)
must set `available = False` and make their channel dropped +
renormalized (`reconstruct.active_weights`), never silently return a
placeholder score, invented Keyman, guessed relationship, fabricated
summary/chat, or invented commitment. A missing signal and a
confidently-negative signal are different things. Keyman extraction,
entity-relationship classification, post summary, in-popup chat, and
commitment derivation go through contextual-orchestrator the same way
adjudication does -- never a raw LLM API. Demo TEPP seed goes through
`tepp_client` the same way: a missing transport or an unused accepted
envelope is Failed (`tepp_not_available` / `tepp_result_not_persisted`),
never a fabricated theta or a local psychometric substitute.

## Tests

```bash
# backend extra compiles fast-mlsirm's PyO3 core -- needs rustc 1.97.1
# (see backend/Dockerfile). Without it, pip falls over at build time.
pip install -e ".[dev,backend]"
pytest
```

Every new channel, fusion rule, or threshold needs a test against
`lineageweave/fixtures.py`'s synthetic dataset (or a new synthetic fixture
in the same spirit) -- never against real data, per the hard rule above.
`backend/tests/` and `tests/test_schema.py` are real-integration tests
against a live local stack (`make up`) and self-skip without one -- see
[README.md](README.md#local-product-stack-docker-compose).

`frontend/` has its own toolchain (Node pinned via `frontend/mise.toml`,
pnpm via Corepack -- do not add a second Node package manager or a
floating Node version):

```bash
cd frontend && pnpm install
pnpm run lint && pnpm run test && pnpm run build
# Storybook inventory (ADR 0020 tokens): pnpm run build-storybook
```

A run-bearing analysis-run registry empties only after an unrevoked
`analysis_run_retention_grant` and `GRANT analysis_run_retention_admin`
(ADR 0020 / v0.87.0). The documented phrase is not a secret. Do not
expose purge on a public HTTP route.

`make seed` writes a Demo Corp lineage run and a TEPP run on the same
snapshot (ADR 0013). The TEPP path goes through `tepp_client`. A missing
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
Opening a cutoff title shows the live post -- compare it with the
cutoff before treating the body as reconstructed evidence (ADR 0016).
`POST /api/analysis-runs` records Pending on an authorized
cutoff capture (ADR 0017) and does not reconstruct lineage.
A thread-group run lists only when an ABAC-visible post exists at or
before `knowledge_cutoff`, even when the signed-in account requested
the run (ADR 0018). Requesting a January thread that has no in-cutoff
visible post does not put that row on the home list. A 404 on that
hidden row must stay generic: do not name the thread or the cutoff.
After that 404, re-read the authorized list so the stale row does
not stay clickable.

## CI gates

`.github/workflows/tests.yml` runs the full suite on every PR to `main`.
Do not weaken, skip, or `continue-on-error` a failing check -- fix the
underlying cause or, for a genuine false positive in a third-party scanner,
add a narrow, documented suppression referencing the specific finding.
## W3C PROV-O boundary

- Add standard provenance through `lineageweave.prov_o` and the
  normalized `provenance_*` schema, never by inventing another
  `edge_type` alias for a W3C property.
- Qualified relations retain their Influence resource and imply the
  corresponding unqualified relation.
- Appendix B inverse names normalize to the preferred W3C direction;
  do not proliferate private inverse vocabulary.
- Keep `knowledge_graph_edge` an explicit navigation projection.

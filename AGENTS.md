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
  multi-channel score fusion (`weighted_convex_fuse` in
  `reconstruct.py`) and the buyer-facing Rankings port
  (`rankweave_client.py`) -- never invent a fused score or a theta.
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

Period leftover pairs (ADR 0028 / 0029) are computed in
`lineageweave/leftover_pairs.py` from the residual after a real
GRM/GPCM score, never invented. Missing cells stay out of the
Gabriel factorization. Closest and farthest post–criterion pairs
persist to `report_leftover_pair` and sit above the member list so
a click opens that post.

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

`POST /api/analysis-runs` records Pending lineage only (ADR 0017 /
v2.7.1). TEPP and period-report kinds 422 before any snapshot write.
`POST /api/analysis-runs/{id}/start` reconstructs a Pending lineage
cutoff bag through `reconstruct()` / `lineage_edge_specs` (ADR 0021 /
v0.88.0). Do not invent a theta.
Opening a cutoff-rewritten title shows **Body this run knew** from
`source_post_revision` beside the live rewrite (ADR 0025 / v2.1.0).
Do not invent the earlier sentence when no revision covers the cutoff.

A corporate-entity similarity result has three outcomes: unique, miss,
or tie (ADR 0026). A tie is not a miss. Keep the organization name
unbound and do not create an `AUTO-` catalog row, even when live name
resolution, hierarchy inference, and verification are available. Keyman
must test the raw organization name before any abbreviation rewrite so a
rewrite cannot turn an existing tie into an apparent creation miss.

R&R chips read the catalog id stored on `post_summary_role`
(ADR 0019 / 0027), including `cataloged_person_id`. Do not rejoin
`corporate_entity` or `cataloged_person` by display name. Historical
backfill leaves a role unbound when two same-named mentions already
exist on the post.

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

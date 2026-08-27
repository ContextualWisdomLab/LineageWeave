# AGENTS.md

Cross-agent conventions for `LineageWeave`, readable by any coding agent
(Claude, Codex, Cursor, opencode, ...). Keep this file tool-agnostic.

## What this repo is

A demo BI prototype that reconstructs git-branch-style lineage between
scattered short records. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
design, [ADR 0084](docs/adr/0084-lineage-research-grounding.md) for the
normative research-grounding policy, and
[`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md) for
supporting literature and aggregate evidence. Event Lineage (reconstructed
post-to-post parents) is distinct from the typed ontology neighborhood
(ADR 0184); source-window continuation is ADR 0124. Do not mix those graphs.

ADRs are the normative source. Research notes, implementation matrices,
runtime-evidence files, and Storybook inventories stay supporting
documents unless an ADR explicitly promotes a decision from them --
[`docs/adr/README.md`](docs/adr/README.md) maps each supporting document
to its governing ADR. Update research notes as literature changes; never
use them to introduce an untracked architecture decision.

## Hard rule: no real data in repository artifacts

This repository ships **synthetic fixtures only** (`lineageweave/fixtures.py`)
and must never commit or expose, by name or otherwise identifiably, any real
organization's records. Never add a real record to a fixture, test case,
screenshot, example, log, benchmark artifact, or documentation. This includes
audit snapshots, gap baselines, PR/issue inventories, and runtime-evidence
documents (for example `docs/product-technical-gap-baseline.md`): aggregate
counts and PR numbers are fine; identifying post identifiers, organization
names, and production record keys are not (ADR 0001).

The private runtime is different: the product is expected to read an
authorized real PostgreSQL source through its configured import/data boundary.
Keep those records outside git and return only authorized, provenance-bearing
product evidence. Validation results brought back into this repository must be
aggregate and non-identifying -- a statistic, never a title, name, or id.

## Reuse before you build

This repo depends on real ContextualWisdomLab-org packages rather than
reimplementing them:

- [ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave) for
  tree assembly (`reconstruct.py`'s `_walk`/`thread_messages` calls).
- [RankWeave](https://github.com/ContextualWisdomLab/RankWeave) for
  multi-channel score fusion (`weighted_convex_fuse` in
  `reconstruct.py`) and the buyer-facing Rankings port
  (`rankweave_client.py`) -- never invent a fused score or a theta.
  Rankings disclose Cormack RRF channel contributions from owned
  rank lists (ADR 0167).
- [TEPP](https://github.com/ContextualWisdomLab/TEPP)'s published wire
  contract for calibrated measurement (`tepp_client.py`) -- never
  reimplement TEPP's model here.
- [contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
  for LLM adjudication (`adjudication_client.py`) -- never call a raw LLM
  API directly from this repo; go through the orchestrator so
  reasoning-effort allocation and cost attribution stay centralized.

Before adding a new dependency, check whether an existing org repo already
does it (`gh repo list ContextualWisdomLab`).

## Decision records and model boundary

- Read the applicable `docs/adr/` records before making an architectural,
  schema, provider, model, or runtime decision. Record a new decision before
  implementing a new policy; do not resolve ADR conflicts by intuition.
- All LLM, VISION, embedding, and structured-output traffic crosses
  `contextual-orchestrator`. This repository never calls a provider API
  directly and never uses a monkey patch to repair an upstream capability.
- Compose loads provider transport credentials from `~/.env` into the
  orchestrator service. Never copy those values into this repository, an
  image, a fixture, a log, or a committed agent configuration.
- `LLM_GATEWAY_MODEL`, `VISION_MODEL`, and provider-specific model selectors
  are not LineageWeave configuration. Model discovery, capability selection,
  reasoning effort, protocol negotiation, and VISION selection belong to
  contextual-orchestrator and must follow its paper-grounded ADRs.
- MLX and any other local runtime are not public provider contracts. Use the
  provider-neutral gateway boundary; historical benchmark material is not
  runtime configuration.

## ADR-first and paper-grounded model decisions

ADRs are normative. Before making an architectural, schema, provider, agent,
LLM, VISION, routing, reasoning-effort, or persistence decision, read the
relevant ADRs first. If the ADR does not cover the decision, write or update
the ADR before changing code, tests, Docker configuration, or runtime policy.
Do not use an implementation preference to silently override an ADR.

Model-related decisions are governed by [ADR
0076](docs/adr/0076-paper-grounded-model-policy.md) and may rely only on the
paper sources cited there and in contextual-orchestrator's literature register:
the Fugu technical report, TRINITY, and Conductor. Provider model ordering,
model-name size guesses, undocumented benchmarks, and local intuition are not
evidence for model quality, routing, reasoning effort, agent count, synthesis,
or VISION selection. If the papers do not support a policy, leave it
undecided or unavailable rather than inventing a heuristic.

The canonical provider credentials are runtime-only from `~/.env` through the
Compose `env_file` boundary. Never copy `~/.env` into the repository or image,
print its values, or persist them. Do not add `LLM_GATEWAY_MODEL`; the upstream
contextual-orchestrator owns model discovery and selection.

## LLM and VISION boundary

- Use `LLM_GATEWAY_API_KEY` and `LLM_GATEWAY_API_URL` from the user's `~/.env`
  at runtime. Keep compatibility aliases only at the process boundary; do not
  introduce a second credential source or a repository-local secret.
- Every LLM and VISION operation goes through contextual-orchestrator. This
  includes adjudication, summaries, Keyman/entity extraction, post chat,
  paragraph structure, image region recognition, OCR, image descriptions, and
  embeddings. Do not call a provider SDK or raw `/v1/chat/completions` or
  `/v1/responses` endpoint from LineageWeave.
- One post shares one orchestrator session id across its LLM and VISION work.
  Pass bounded provenance metadata with each request, including post id,
  corporate entity code, PU, author id, source system, and visibility when
  available. Do not persist an ad hoc `user_account + post_id` session key;
  use normalized third-normal-form tables and the ADR-defined foreign keys.
- Do not set `LLM_GATEWAY_MODEL` or select a model by provider order, model
  name, parameter count, or local intuition. Blank provider agents must be
  expanded and selected by contextual-orchestrator. Reasoning effort defaults
  to `auto`; `low`, `medium`, `high`, and `xhigh` are capability/paper-policy
  inputs, not a local model ranking heuristic. Never force `none` merely
  because a model is not known to be a reasoning model.
- Responses API `developer` and Chat Completions `system` are compatible
  instruction roles at the orchestrator boundary. The orchestrator owns the
  translation and provider capability handling; do not fork prompts per
  transport in this repository.
- Treat `LLM_GATEWAY_API_URL` as an opaque OpenAI-compatible gateway endpoint.
  Do not add MLX/local-server URL schemes, port lists, local defaults,
  chat-template injection, or vendor-specific bootstrap exceptions in
  LineageWeave. Provider-specific capability translation belongs upstream.
- `response_format`, `tools`, Responses API requests, `json_object`, and
  `json_schema` must remain multi-agent workflows. A structured response or a
  repair attempt must not silently fall back to a single-agent passthrough.
  Preserve schema validation, synthesis, repair, session, and cost lineage.
- VISION is an orchestrator capability, not a frontend-only enhancement. For
  unsupported image formats, convert at ingestion; for transparent PNGs,
  flatten transparent pixels onto white for the derived analysis image while
  retaining the original asset and provenance. Recognize image DOM/visual
  regions before OCR, descriptions, Keyman extraction, or embeddings. Store
  region-level evidence and show each region's bounding range beside its
  caption and OCR (ADR 0155); never show an internal LLM instruction such as
  `This post is an image` to a buyer.

## Observability boundary

- Follow governance-risk-compliance ADR 0009 and LineageWeave ADR 0122 for
  OpenTelemetry. Use `OTEL_SERVICE_NAME` and
  `OTEL_EXPORTER_OTLP_ENDPOINT`; exporting is opt-in and provider-neutral.
- Correlate one post's HTTP, contextual-orchestrator, and Valkey work with the
  existing post-scoped session metadata. Do not create an ad hoc session table.
- Telemetry may contain bounded operation, route-template, service-peer, and
  correlation attributes, but never post body, prompt, answer, source content,
  actor or tenant identifiers, credentials, raw stream keys, or provider
  responses. GRC remains the control/evidence owner.

## Source parsing and semantic units

- Preserve the source representation and provenance, then derive semantic
  paragraph/list/table/image-region units for search, ontology, and embeddings.
  Do not flatten a post into one opaque body string.
- Paragraph structure may come from HTML DOM and CSS, visible leading spaces or
  `&nbsp;`, and OOXML/MS Word paragraph or run properties. Combine those
  signals with contextual-orchestrator adjudication when evidence conflicts;
  heuristics are not authoritative and must not be the only fallback for an
  unresolved structure decision.
- Source-system codes may be enriched with catalog display names under ADR
  0117. Pass those names to contextual-orchestrator as labeled lookup hints
  only; never promote them to an entity binding, customer fact, project fact,
  or imported-author affiliation without post evidence.
- Remove presentation-only visual line alignment inside a paragraph (for
  example continuation lines manually aligned after `-`, `*`, `1.`, or `.`)
  from derived semantic text, while retaining the source body and meaningful
  list/heading nesting. A buyer-facing post view must render semantic
  paragraphs, not the authoring application's spacing workaround.
- Quantity HTML `<sup>`/`<sub>` and caret exponents such as `m^3` become
  Unicode in derived units and React `<sup>`/`<sub>` in the post view
  (ADR 0165). Never assign the body to `innerHTML`. Do not treat
  `qty < 50` or a leading footnote `^1` as an exponent.
- Image descriptions, OCR text, and region evidence are analysis artifacts,
  not buyer-facing prompt instructions. Buyer UI shows the source content and
  useful captions/evidence only, with provenance where appropriate.

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

The lineage `text` channel follows [ADR 0190](docs/adr/0190-lineage-text-channel-embedding-swap.md):
when an embedding provider is configured, `reconstruct()` precomputes
batched label embeddings once per reconstruction and scores cosine
similarity; `difflib` character overlap is only the fallback for a pair
whose vector is missing. Clamp the raw cosine into `[0, 1]` -- do not
remap it from `[-1, 1]`, because real sentence embeddings occupy an
anisotropic cone (unrelated pairs already score a modestly positive
cosine) and the remap manufactures false weak positives. A missing
vector degrades that pair back to difflib; it never fabricates a score.

## Measurement boundary

- Channel-weight estimation stays unavailable until an independent
  lineage anchor exists ([ADR 0145](docs/adr/0145-psychometric-channel-weight-estimation.md)).
  Do not fit an unanchored IRT model over candidate pairs and promote its
  latent factor to "relatedness"; `scripts/estimate_channel_weights.py`
  must keep exiting without writing. The hand-picked constants in
  `DEFAULT_CHANNEL_WEIGHTS` are an explicitly ungrounded compatibility
  fallback -- never present them as calibrated or paper-grounded
  measurement.
- Persisted channel-weight vectors fail closed: malformed,
  mixed-provenance, or unsupported-anchor rows are ignored, not
  renormalized or repaired.
- Caller-mapped grouping values stay raw in their source-provenance
  columns across backfill and re-import; normalization happens only in
  derived reconstruction fields.
- Per-edge channel breakdowns persist to nullable
  `post_lineage_edge.channel_scores` jsonb ([ADR 0195](docs/adr/0195-lineage-edge-channel-scores-persistence.md)):
  a missing breakdown means the edge predates the column -- an honest
  unknown, never zero-filled or reconstructed. It exists for direct
  database diagnosis only; exposing it through an API or UI needs its own
  decision first.

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

`tests/test_public_docstrings.py` enforces repository-wide docstring
coverage: every public function and class under `lineageweave/` and
`backend/app/` (non-underscore names, `__init__.py` excluded) carries a
docstring. Ship new public definitions documented; the gate fails the PR
otherwise.

### Schema migrations

Migrations 0001–0011 are the non-idempotent image bootstrap and replay
only on an empty data directory. Everything numbered 0012 or later must be
safe to replay and is applied automatically by
`docker/postgres-init/migrate.sh` in sorted filename order -- one fixed
lower-bound pattern, no per-file allowlist ([ADR 0166](docs/adr/0166-idempotent-migration-replay-window.md)).
Prefer native idempotency (`IF NOT EXISTS`, `ON CONFLICT`); a migration
that cannot be made idempotent requires a migration-ledger ADR first.
Each accepted file runs with `psql -X -v ON_ERROR_STOP=1`, so a failure
stops startup instead of leaving a healthy-looking partial schema, and
application code must not compensate for a missing table.

Period leftover pairs (ADR 0017 / 0018 / 0048 / 0049 / 0119 / 0158 / 0162 /
0163 / 0164 / 0182 / 0185 / 0201 / 0233) are computed in `lineageweave/leftover_pairs.py` from the
residual after a real GRM/GPCM score, never invented. Distances are
Euclidean on the two-dimensional Gabriel leftover map; missing cells stay
out of the factorization. Closest and farthest post–criterion pairs
persist to `report_leftover_pair` with signed residual `R`, observed
`Y`, and expected `E[Y|θ, item]` so `R = Y − E` remains auditable,
plus leftover-map rank so rank 0 is not read as structure,
unexplained leftover, the ADR 0201 reconstruction evidence, ADR 0185
cross-share evidence, and ADR 0233 unexplained leftover share
`s = U² / R²`. ADR 0201 is the sole normative reconstruction formula,
storage, and audit contract; do not duplicate or reinterpret it here.
ADR 0233 is the sole unexplained leftover share contract; do not persist
leftover-map explained share `e` here. The pairs sit above the member
list so a click opens that post with the leftover criterion current
in Post quality (ADR 0158). Leftover-map axis share (ADR 0148) is Gabriel inertia of
residual SVD axes 1 and 2 and persists to `report_leftover_map_axis`.
Rank-0 residuals emit two zero-share axes; the shares are report-level
and are not a leftover score. Complete-case coverage (ADR 0168) persists to
`report_leftover_map_coverage` and captions the pair list with how
many scored posts entered the map.

Global Ask relative-time filters (ADR 0150 / 0202) bind to
`source_post.event_occurred_at` and fall back to `created_at` only
when the event instant is missing. Cited evidence names **Time
axis** so the reader can open that post and see which clock
matched. Do not invent an event date or a theta.

Organization chips show a unique search-corroborated SKOS companion
(`Demo Corp (DC)`) and stay unlabeled on a miss or tie (ADR 0008 /
ADR 0170). Do not invent an abbreviation from letters. Synthetic
fixtures only.

The grouping comparison strip (ADR 0149) reuses the authorized leftover
pair store described above; a leftover pair for a hidden post is
omitted.

`frontend/` has its own toolchain (Node pinned via `frontend/mise.toml`,
pnpm via Corepack -- do not add a second Node package manager or a
floating Node version):

```bash
cd frontend && pnpm install
pnpm run lint && pnpm run test && pnpm run build
# Storybook inventory: pnpm run build-storybook
```

Repeated web objects use `frontend/src/styles/tokens.css`, not inline hex
(ADR 0099 badge/accent tokens, with dark-mode overrides guarded by
`tokens.test.ts`); new stories belong in the inventory at
`docs/storybook-inventory.md`.

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

## Ontology publication boundary

The ontology namespace publishes as a deterministic GitHub Pages artifact
([ADR 0159](docs/adr/0159-published-ontology-pages.md)): render through
`scripts/build_ontology_site.py` (same source tree produces the same
bytes -- no build timestamps, source SHA-256 manifest) and deploy only
through the fail-closed `scripts/publish_ontology_site.py` from `main`.
A manual dispatch from another ref is not a publication path. The
repository-case public namespace
`https://contextualwisdomlab.github.io/LineageWeave/ontology#` is
canonical ([ADR 0207](docs/adr/0207-repository-case-ontology-namespace-canonical.md),
superseding ADR 0157, resolving issue #372); the lowercase form is a
deprecated compatibility vocabulary with validated term-kind mappings.
New runtime values, exports, fixtures, and database rows mint only
repository-case IRIs; `scripts/migrate_legacy_namespace.py` rewrites
stored lowercase IRIs (dry-run by default, never touching provenance
columns). Do not silently rewrite either historical form. The SHACL
shapes graph (`docs/ontology/lineageweave-kg-shapes.ttl`) is the
closed-world data-validation boundary for DB-to-RDF projections and is
published beside the ontology.

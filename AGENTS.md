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
`tests/test_source_post_voice_history_live.py` is the same pattern for
ADR 0252 A → B → A cutoff and concurrent primary-Voice history.

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
0163 / 0164 / 0182 / 0185 / 0201 / 0233 / 0266 / 0267 / 0268 / 0269 / 0270 / 0271 / 0272 / 0273 / 0274 / 0275 / 0276 / 0277 / 0278 / 0279 / 0280 / 0281 / 0282 / 0283 / 0284 / 0285 / 0286 / 0287 / 0288 / 0289 / 0290 / 0291 / 0292 / 0293 / 0294 / 0295 / 0296 / 0297 / 0298 / 0299 / 0300 / 0301 / 0302 / 0303 / 0304 / 0305 / 0306 / 0307 / 0308 / 0309 / 0310 / 0311 / 0312 / 0313 / 0314 / 0315 / 0316 / 0317 / 0318 / 0319 / 0320 / 0321 / 0322 / 0323 / 0324 / 0325 / 0326 / 0327 / 0328) are computed in `lineageweave/leftover_pairs.py` from the
residual after a real GRM/GPCM score, never invented. Distances are
Euclidean on the two-dimensional Gabriel leftover map; missing cells stay
out of the factorization. Closest and farthest post–criterion pairs
persist to `report_leftover_pair` with signed residual `R`, observed
`Y`, and expected `E[Y|θ, item]` so `R = Y − E` remains auditable,
plus leftover-map rank so rank 0 is not read as structure,
unexplained leftover, the ADR 0201 reconstruction evidence, ADR 0185
cross-share evidence, ADR 0233 unexplained leftover share
`s = U² / R²`, ADR 0266 explained leftover share `e = R̂² / R²`, and
ADR 0267 leftover-map coordinates `ξ_{1:2}` / `ζ_{1:2}`.
ADR 0201 is the sole normative reconstruction formula,
storage, and audit contract; do not duplicate or reinterpret it here.
ADR 0233 is the sole unexplained leftover share contract. ADR 0266 is
the sole explained leftover share contract. ADR 0267 is the sole
leftover-map coordinate contract. ADR 0268 is the leftover-map
graphic-display contract: draw persisted `ξ` and `ζ` above the pair
buttons; omit the plot when coordinates are missing; click a post
marker to open that post. ADR 0269 captions those leftover-map axes
with persisted leftover-map axis share `σ_k² / Σ_j σ_j²` when finite,
including rank-0 zero-share axes; a missing or non-finite share omits
that axis badge and keeps the existing leftover-map axis text. ADR 0270
ticks leftover-map axes at the origin and at each unique finite
persisted `ξ` / `ζ` coordinate so the pair-row badge matches the
plot; rank-0 unused axes name only `0` and do not invent drawing-scale
ticks. ADR 0271 captions leftover-map pair segments with persisted
leftover-map distance `d` so the pair-row badge matches the graphic;
a missing or non-finite `d` omits that segment caption and does not
invent `d` from plotted coordinates. ADR 0272 captions leftover-map
pair segments with persisted leftover-map reconstruction `R̂` so the
pair-row badge matches the graphic; a missing or non-finite `R̂` omits
that reconstruction caption and does not invent `R̂` from plotted
coordinates. ADR 0273 captions leftover-map pair segments with persisted
leftover-map explained leftover share `e` so the pair-row `R̂²/R²`
badge matches the graphic; a missing or non-finite `e` omits that
explained leftover share caption and does not invent `e` from `R̂` and
`R` or from plotted coordinates. ADR 0274 captions leftover-map pair
segments with persisted leftover-map unexplained leftover share `s` so
the pair-row `U²/R²` badge matches the graphic; a missing or non-finite
`s` omits that unexplained leftover share caption and does not invent
`s` from `U` and `R` or from plotted coordinates. ADR 0275 captions leftover-map pair
segments with persisted leftover-map cross share `x` so
the pair-row `2R̂U/R²` badge matches the graphic; a missing or non-finite
`x` omits that leftover-map cross share caption and does not invent
`x` from `R̂`, `U`, and `R` or from plotted coordinates. ADR 0276 captions leftover-map pair
segments with persisted leftover-map unexplained leftover `U` so
the pair-row `U` badge matches the graphic; a missing or non-finite
`U` omits that unexplained leftover caption and does not invent
`U` from `R` and `R̂` or from plotted coordinates. ADR 0277 captions leftover-map pair
segments with persisted leftover residual `R` so the pair-row residual
badge matches the graphic; a missing or non-finite `R` omits that leftover
residual caption and does not invent `R` from `Y` and `E`, from `U` and
`R̂`, or from plotted coordinates. ADR 0278 captions leftover-map pair
segments with persisted leftover observed `Y` so the pair-row `Y` badge
matches the graphic; a missing or non-finite `Y` omits that leftover
observed caption and does not invent `Y` from `R` and `E` or from plotted
coordinates. ADR 0279 captions leftover-map pair
segments with persisted leftover expected `E` so the pair-row `E` badge
matches the graphic; a missing or non-finite `E` omits that leftover
expected caption and does not invent `E` from `Y` and `R` or from plotted
coordinates. ADR 0280 captions leftover-map pair
segments with persisted leftover-map rank so the pair-row `rank` badge
matches the graphic; a missing, negative, or non-integer rank omits that
leftover-map rank caption and does not invent rank from plotted
coordinates, leftover-map distance, or the count of unused axes. ADR 0281
captions the leftover-map graphic display with persisted leftover-map
complete-case coverage so the pair-list `used N of M scored posts` note
matches the plot; a missing, non-integer, negative-used, non-positive-scored,
or used-greater-than-scored coverage omits that leftover-map coverage caption
and does not invent coverage from plotted marker count. ADR 0282 captions the
leftover-map graphic display with persisted leftover-map item complete-case
coverage so two criterion diamonds are not read as the scored-criterion census;
a missing, non-integer, negative-used, non-positive-scored, or
used-greater-than-scored item coverage omits that leftover-map item coverage
caption and does not invent item coverage from plotted criterion marker count.
ADR 0283 captions the leftover-map graphic display with persisted leftover-map
incomplete post coverage so a `used N of M` caption is not read as every
scored post entering the map; a missing, non-integer, or negative dropped
count, or a dropped count that contradicts usable complete-case integers,
omits that leftover-map incomplete post caption and does not invent dropped
posts from scored minus used or from plotted marker count.
ADR 0284 captions the leftover-map graphic display with persisted leftover-map
incomplete item coverage so a `used N of M scored criteria` caption is not
read as every scored criterion entering the map; a missing, non-integer, or
negative dropped count, or a dropped count that contradicts usable item
complete-case integers, omits that leftover-map incomplete item caption and
does not invent dropped criteria from scored minus used or from plotted
criterion marker count.
ADR 0285 captions the leftover pair list with persisted leftover-map item
complete-case coverage so a `used N of M scored posts` note is not read as
the scored-criterion census; a missing, non-integer, negative-used,
non-positive-scored, or used-greater-than-scored item coverage omits that
leftover-map item coverage note and does not invent item coverage from
plotted criterion marker count.
ADR 0286 captions the leftover pair list with persisted leftover-map
incomplete post coverage so a `used N of M scored posts` note is not read as
every scored post entering the map; a missing, non-integer, or negative
dropped count, or a dropped count that contradicts usable complete-case
integers, omits that leftover-map incomplete post note and does not invent
dropped posts from scored minus used or from plotted marker count.
ADR 0287 captions the leftover pair list with persisted leftover-map
incomplete item coverage so a `used N of M scored criteria` note is not read as
every scored criterion entering the map; a missing, non-integer, or negative
dropped count, or a dropped count that contradicts usable item complete-case
integers, omits that leftover-map incomplete item note and does not invent
dropped criteria from scored minus used or from plotted criterion marker count.
ADR 0288 fail-closes leftover-map post complete-case coverage on the pair list
through leftoverMapCoverageCounts so a used-greater-than-scored, negative, or
non-integer payload cannot caption a contradictory `used N of M scored posts`
note; a missing, non-integer, negative-used, non-positive-scored, or
used-greater-than-scored coverage omits that leftover-map coverage note and
does not invent post coverage from plotted marker count.
ADR 0289 captions the grouping comparison strip with persisted leftover-map
post complete-case coverage through leftoverMapCoverageCounts so a buyer who
compares leftover pairs can read how many scored posts entered each grouping's
Gabriel factorization; a missing, non-integer, negative-used, non-positive-scored,
or used-greater-than-scored coverage omits that leftover-map comparison coverage
note and does not invent post coverage from leftover pair count or plotted
marker count. The strip does not gain leftover-map incomplete post coverage,
leftover-map incomplete item coverage, or the leftover-map graphic.
ADR 0290 captions the grouping comparison strip with persisted leftover-map
item complete-case coverage through leftoverMapItemCoverageCounts so a buyer who
compares leftover pairs can read how many scored criteria entered each grouping's
Gabriel factorization; a missing, non-integer, negative-used, non-positive-scored,
or used-greater-than-scored item coverage omits that leftover-map comparison item
coverage note and does not invent item coverage from leftover pair count or plotted
criterion marker count.
ADR 0291 captions the grouping comparison strip with persisted leftover-map
incomplete post coverage through leftoverMapIncompletePostCount so a buyer who
compares leftover pairs can read how many scored posts stayed out of each grouping's
Gabriel factorization; a missing, non-integer, or negative dropped count, or a
dropped count that contradicts usable complete-case integers, omits that leftover-map
comparison incomplete post note and does not invent dropped posts from scored minus
used or from leftover pair count. Dropped `0` is shown when persisted. The strip
does not gain leftover-map incomplete item coverage or the leftover-map graphic.
ADR 0292 captions the grouping comparison strip with persisted leftover-map
incomplete item coverage through leftoverMapIncompleteItemCount so a buyer who
compares leftover pairs can read how many scored criteria stayed out of each grouping's
Gabriel factorization; a missing, non-integer, or negative dropped count, or a
dropped count that contradicts usable item complete-case integers, omits that leftover-map
comparison incomplete item note and does not invent dropped criteria from scored minus
used or from leftover pair count. Dropped `0` is shown when persisted. The strip
does not gain the leftover-map graphic.
ADR 0293 captions grouping comparison leftover-pair buttons with persisted leftover-map
reconstruction `R̂` through formatLeftoverMapReconstruction so a buyer who compares
leftover pairs can match the pair-row reconstruction badge; a missing or non-finite
`R̂` omits that leftover-map comparison reconstruction badge and does not invent `R̂`
from leftover-map distance or plotted coordinates. The strip does not gain the
leftover-map graphic.
ADR 0294 captions grouping comparison leftover-pair buttons with persisted leftover-map
explained leftover share `e` through formatLeftoverMapExplainedShare so a buyer who
compares leftover pairs can match the pair-row `R̂²/R²` badge; a missing or non-finite
`e` omits that leftover-map comparison explained leftover share badge and does not invent
`e` from `R̂` and `R` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0295 captions grouping comparison leftover-pair buttons with persisted leftover-map
unexplained leftover share `s` through formatLeftoverMapUnexplainedShare so a buyer who
compares leftover pairs can match the pair-row `U²/R²` badge; a missing or non-finite
`s` omits that leftover-map comparison unexplained leftover share badge and does not invent
`s` from `U` and `R` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0296 captions grouping comparison leftover-pair buttons with persisted leftover-map
cross share `x` through formatLeftoverMapCrossShare so a buyer who
compares leftover pairs can match the pair-row `2R̂U/R²` badge; a missing or non-finite
`x` omits that leftover-map comparison cross share badge and does not invent
`x` from `R̂`, `U`, and `R` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0297 captions grouping comparison leftover-pair buttons with persisted leftover-map
unexplained leftover `U` through formatLeftoverMapUnexplained so a buyer who
compares leftover pairs can match the pair-row `U` badge; a missing or non-finite
`U` omits that leftover-map comparison unexplained leftover badge and does not invent
`U` from `R` and `R̂` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0298 captions grouping comparison leftover-pair buttons with persisted leftover
residual `R` through formatLeftoverMapResidual so a buyer who
compares leftover pairs can match the pair-row `R` badge; a missing or non-finite
`R` omits that leftover-map comparison residual badge and does not invent
`R` from `Y` and `E` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0299 captions grouping comparison leftover-pair buttons with persisted leftover
observed `Y` through formatLeftoverMapObserved so a buyer who
compares leftover pairs can match the pair-row `Y` badge; a missing or non-finite
`Y` omits that leftover-map comparison observed badge and does not invent
`Y` from `R` and `E` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0300 captions grouping comparison leftover-pair buttons with persisted leftover
expected `E` through formatLeftoverMapExpected so a buyer who
compares leftover pairs can match the pair-row `E` badge; a missing or non-finite
`E` omits that leftover-map comparison expected badge and does not invent
`E` from `Y` and `R` or from leftover-map distance. The strip does not gain the
leftover-map graphic.
ADR 0301 captions grouping comparison leftover-pair buttons with persisted leftover-map
rank through formatLeftoverMapRank so a buyer who
compares leftover pairs can match the pair-row `rank` badge; a missing, negative, or
non-integer rank omits that leftover-map comparison rank badge and does not invent
rank from plotted coordinates, leftover-map distance, or the count of unused axes.
The strip does not gain the leftover-map graphic.
ADR 0302 captions grouping comparison leftover-pair buttons with persisted leftover-map
coordinates `ξ` / `ζ` through formatLeftoverMapCoordinates so a buyer who
compares leftover pairs can match the pair-row coordinate badge; a missing or
non-finite axis omits that leftover-map comparison coordinates badge and does not
invent coordinates from leftover-map rank, leftover-map distance, leftover-map
reconstruction, or leftover residual. The strip does not gain the leftover-map graphic.
ADR 0303 returns persisted leftover-map coordinates `ξ` / `ζ` on
`GET /api/reports/compare/{period}` leftover pairs so a buyer who
compares leftover pairs can match the pair-row coordinate badge on live
responses; a missing axis stays null and does not invent coordinates from
leftover-map rank, leftover-map distance, leftover-map reconstruction, or
leftover residual. ADR 0304 draws the leftover-map graphic display of those
already-named `ξ` / `ζ` coordinates above grouping comparison leftover-pair
buttons when four leftover-map axes are finite; a missing or non-finite axis
omits that pair from the comparison graphic and does not invent coordinates
from leftover-map rank, leftover-map distance, leftover-map reconstruction, or
leftover residual. Omit the comparison graphic when no leftover pair has four
finite leftover-map coordinates. ADR 0305 returns persisted leftover-map axes on
`GET /api/reports/compare/{period}` and captions leftover-map axis share on the
grouping comparison leftover-map graphic when that share is finite; a missing or
non-finite share omits that leftover-map comparison axis share badge and keeps
leftover map comparison axis text. Do not invent leftover-map axis share from
leftover-map rank, leftover-map distance, leftover-map reconstruction, leftover
residual, leftover pair count, or the count of unused axes.
ADR 0306 captions leftover-map complete-case coverage on that grouping
comparison leftover-map graphic when leftoverMapCoverageCounts returns usable
complete-case integers; a missing, non-integer, negative-used, non-positive-scored,
or used-greater-than-scored coverage omits that leftover-map comparison graphic
coverage caption and keeps leftover map comparison axis share when finite.
Do not invent leftover-map coverage from plotted marker count, leftover pair
count, leftover-map rank, leftover-map distance, leftover-map axis share,
leftover-map reconstruction, leftover residual, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage,
or the count of unused axes. ADR 0307 captions leftover-map item complete-case
coverage on that grouping comparison leftover-map graphic when leftoverMapItemCoverageCounts
returns usable complete-case integers; a missing, non-integer, negative-used,
non-positive-scored, or used-greater-than-scored item coverage omits that leftover-map
comparison graphic item coverage caption and keeps leftover-map comparison graphic
coverage when leftoverMapCoverageCounts returns usable complete-case integers.
Do not invent leftover-map item coverage from plotted criterion marker count,
leftover pair count, leftover-map rank, leftover-map distance, leftover-map
axis share, leftover-map reconstruction, leftover residual, leftover-map post
coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. ADR 0308 captions leftover-map
incomplete post coverage on that grouping comparison leftover-map graphic when leftoverMapIncompletePostCount
returns a usable dropped integer; a missing, negative, non-integer, or scored-minus-used
mismatch omits that leftover-map comparison graphic incomplete posts caption and keeps leftover-map
comparison graphic coverage and leftover-map comparison graphic item coverage when those helpers
return usable complete-case integers. Do not invent leftover-map incomplete posts from scored minus
used, plotted marker count, leftover pair count, leftover-map rank, leftover-map distance,
leftover-map axis share, leftover-map reconstruction, leftover residual, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete item coverage, or the count of unused
axes. ADR 0309 captions leftover-map incomplete item coverage on that grouping comparison leftover-map
graphic when leftoverMapIncompleteItemCount returns a usable dropped integer; a missing, negative,
non-integer, or scored-minus-used mismatch omits that leftover-map comparison graphic incomplete items
caption and keeps leftover-map comparison graphic coverage, leftover-map comparison graphic item
coverage, and leftover-map comparison graphic incomplete posts when those helpers return usable
integers. Do not invent leftover-map incomplete items from scored minus used, plotted criterion
marker count, leftover pair count, leftover-map rank, leftover-map distance, leftover-map axis
share, leftover-map reconstruction, leftover residual, leftover-map post coverage, leftover-map
item coverage, leftover-map incomplete post coverage, or the count of unused axes.
ADR 0310 captions leftover-map reconstruction on that grouping comparison leftover-map
graphic when formatLeftoverMapReconstruction returns a usable signed badge; a missing or
non-finite `R̂` omits that leftover-map comparison graphic reconstruction caption and keeps
leftover-map distance `d`, leftover-map comparison graphic coverage, leftover-map comparison
graphic item coverage, leftover-map comparison graphic incomplete posts, and leftover-map
comparison graphic incomplete items when those helpers return usable integers. Do not invent
`R̂` from leftover-map distance, plotted coordinates, leftover residual, leftover-map rank,
leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0311 captions leftover-map explained leftover share on that grouping comparison leftover-map
graphic when formatLeftoverMapExplainedShare returns a usable badge; a missing or
non-finite `e` omits that leftover-map comparison graphic explained leftover share caption and keeps
leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`e` from leftover-map reconstruction, leftover residual, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0312 captions leftover-map unexplained leftover share on that grouping comparison leftover-map
graphic when formatLeftoverMapUnexplainedShare returns a usable badge; a missing or
non-finite `s` omits that leftover-map comparison graphic unexplained leftover share caption and keeps
leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`s` from `U` and `R`, leftover-map reconstruction, leftover residual, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0313 captions leftover-map cross share on that grouping comparison leftover-map
graphic when formatLeftoverMapCrossShare returns a usable badge; a missing or
non-finite `x` omits that leftover-map comparison graphic cross share caption and keeps
leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`x` from `R̂`, `U`, and `R`, leftover-map reconstruction, leftover residual, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0314 captions leftover-map unexplained leftover on that grouping comparison leftover-map
graphic when formatLeftoverMapUnexplained returns a usable badge; a missing or
non-finite `U` omits that leftover-map comparison graphic unexplained leftover caption and keeps
leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`U` from `R` and `R̂`, leftover-map reconstruction, leftover residual, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0315 captions leftover residual on that grouping comparison leftover-map
graphic when formatLeftoverMapResidual returns a usable badge; a missing or
non-finite `R` omits that leftover-map comparison graphic leftover residual caption and keeps
leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`R` from `Y` and `E`, from `U` and `R̂`, leftover-map reconstruction, leftover-map unexplained leftover, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0316 captions leftover observed on that grouping comparison leftover-map
graphic when formatLeftoverMapObserved returns a usable badge; a missing or
non-finite `Y` omits that leftover-map comparison graphic leftover observed caption and keeps
leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`Y` from `R` and `E`, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0317 captions leftover expected on that grouping comparison leftover-map
graphic when formatLeftoverMapExpected returns a usable badge; a missing or
non-finite `E` omits that leftover-map comparison graphic leftover expected caption and keeps
leftover observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
`E` from `Y` and `R`, leftover observed, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map distance, plotted coordinates,
leftover-map rank, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0318 captions leftover-map rank on that grouping comparison leftover-map
graphic when formatLeftoverMapRank returns a usable badge; a missing,
negative, or non-integer rank omits that leftover-map comparison graphic leftover-map rank caption and keeps
leftover expected `E`, leftover observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
leftover-map rank from plotted coordinates, leftover-map distance, leftover expected, leftover observed, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0319 captions leftover-map distance on that grouping comparison leftover-map
graphic when formatLeftoverMapDistance returns a usable badge; a missing or
non-finite `d` omits that leftover-map comparison graphic leftover-map distance caption and keeps
leftover-map rank, leftover expected `E`, leftover observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map comparison graphic coverage,
leftover-map comparison graphic item coverage, leftover-map comparison graphic incomplete posts,
and leftover-map comparison graphic incomplete items when those helpers return usable integers. Do not invent
leftover-map distance from plotted coordinates, leftover-map rank, leftover expected, leftover observed, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0320 captions leftover-map coordinate ticks on that grouping comparison leftover-map
graphic from already-named leftover-map coordinates; the origin and each unique finite
persisted `ξ` / `ζ` projection still name leftover-map comparison graphic leftover-map axis
ticks. Do not invent evenly spaced leftover-map comparison graphic leftover-map axis ticks
that no persisted coordinate occupies. Do not invent leftover-map coordinate ticks from leftover-map
distance, leftover-map rank, leftover expected, leftover observed, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map axis share, leftover-map post coverage, leftover-map item coverage,
leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair
count, or the count of unused axes.
ADR 0321 captions leftover-map singular values on that grouping comparison leftover-map
graphic from already-named leftover-map axes when that persisted `σ_k` is finite and
non-negative. Rank-0 unused axes still name leftover-map comparison graphic leftover-map
axis `σ 0.00`. Share and singular value omit independently. Do not invent leftover-map
singular values from leftover-map axis share, leftover-map coordinate ticks, leftover-map
distance, leftover-map rank, leftover expected, leftover observed, leftover residual,
leftover-map unexplained leftover, leftover-map reconstruction, leftover-map post coverage,
leftover-map item coverage, leftover-map incomplete post coverage, leftover-map incomplete
item coverage, leftover pair count, or the count of unused axes.
ADR 0322 captions leftover-axis report badges with persisted leftover-map singular
values `σ_k` when leftoverMapAxisBadgeSingular returns a usable finite non-negative
value; a missing, non-finite, or negative singular value omits that `σ` badge and
keeps `leftover axis {k} {share}%`. Do not invent leftover-map singular values from
leftover-map axis share. ADR 0323 captions leftover-axis report badges on the grouping
comparison strip with persisted leftover-map singular values `σ_k` when
leftoverMapCompareAxisBadge returns a usable leftover-axis caption. Distinct accessible
name `leftover map comparison leftover axis {axis} σ {value}`. Share and singular value
omit independently. Rank-0 unused axes still name `σ 0.00`. Do not invent leftover-map
singular values from leftover-map axis share.
ADR 0324 captions leftover-map graphic-display axes with persisted leftover-map singular
values `σ_k` when leftoverMapPlotAxisBadge returns a usable leftover-map axis caption.
Distinct accessible name `leftover-map axis {axis} σ {value} ({share}%)`. Share and
singular value omit independently. Rank-0 unused axes still name leftover-map axis
`σ 0.00`. Do not invent leftover-map singular values from leftover-map axis share.
ADR 0325 captions leftover-axis report badges with persisted leftover-map singular
values `σ_k` independently of leftover-map axis share when leftoverMapAxisBadge
returns a usable leftover-axis caption. Distinct accessible name
`leftover axis {axis} σ {value}`. Share and singular value omit independently.
Rank-0 unused axes still name leftover-axis `σ 0.00`. Do not invent leftover-map
singular values from leftover-map axis share. Do not invent leftover-map axis
share from leftover-map singular values.
ADR 0326 captions leftover-map comparison graphic leftover-map axes with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotAxisBadge returns a usable leftover-map
axis caption. Distinct accessible name
`leftover map comparison graphic leftover-map axis {axis} σ {value}`. Share and
singular value omit independently. Rank-0 unused axes still name leftover-map
comparison graphic leftover-map axis `σ 0.00`. Do not invent leftover-map
singular values from leftover-map axis share. Do not invent leftover-map axis
share from leftover-map singular values.
ADR 0327 captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapPlotTickAxisBadge returns a usable leftover-map
axis tick caption. Distinct accessible name
`leftover-map axis {axis} tick {value} σ {singular}`. Singular value omits independently
of leftover-map axis share. Leftover-map graphic leftover-map axis ticks never name leftover-map
axis share. Rank-0 unused axes still name leftover-map graphic leftover-map axis tick
`σ 0.00`. Do not invent leftover-map singular values from leftover-map axis share.
ADR 0328 captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map
axis tick caption. Distinct accessible name
`leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}`. Singular value omits independently
of leftover-map axis share. Leftover-map comparison graphic leftover-map axis ticks never name leftover-map
axis share. Rank-0 unused axes still name leftover-map comparison graphic leftover-map axis tick
`σ 0.00`. Do not invent leftover-map singular values from leftover-map axis share.
ADR 0329 captions leftover-map comparison leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapCompareAxisTickBadge returns a usable leftover-axis
tick caption. Distinct accessible name
`leftover map comparison leftover axis {axis} tick {value} σ {singular}`. Singular value omits independently
of leftover-map axis share. Leftover-map comparison leftover-axis ticks never name leftover-map
axis share. Rank-0 unused axes still name leftover-map comparison leftover-axis tick
`σ 0.00`. Do not invent leftover-map singular values from leftover-map axis share. Do not invent leftover-map
axis share from leftover-map singular values. This increment does not change leftover-map comparison graphic leftover-map
axis ticks.
ADR 0330 captions leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapAxisTickBadge returns a usable leftover-axis
tick caption. Distinct accessible name
`leftover axis {axis} tick {value} σ {singular}`. Singular value omits independently
of leftover-map axis share. Leftover-axis ticks never name leftover-map
axis share. Rank-0 unused axes still name leftover-axis tick
`σ 0.00`. Do not invent leftover-map singular values from leftover-map axis share. Do not invent leftover-map
axis share from leftover-map singular values. This increment does not change leftover-map comparison leftover-axis
ticks.
ADR 0331 captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption. Distinct accessible names
`leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%` and
`leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%`.
Share and singular value omit independently. Rank-0 unused axes still name leftover-map
comparison graphic leftover-map axis tick leftover-map axis share `0%`. Do not invent leftover-map
axis share from leftover-map singular values. Do not invent leftover-map singular values from leftover-map
axis share. Leftover-map graphic leftover-map axis ticks, leftover-map comparison leftover-axis ticks,
and leftover-axis ticks never name leftover-map axis share this increment.
ADR 0332 captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapPlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption. Distinct accessible names
`leftover-map axis {axis} tick {value} {share}%` and
`leftover-map axis {axis} tick {value} σ {singular} {share}%`.
Share and singular value omit independently. Rank-0 unused axes still name leftover-map
graphic leftover-map axis tick leftover-map axis share `0%`. Do not invent leftover-map
axis share from leftover-map singular values. Do not invent leftover-map singular values from leftover-map
axis share. Leftover-map comparison graphic leftover-map axis ticks, leftover-map comparison leftover-axis ticks,
and leftover-axis ticks never name leftover-map axis share this increment.
ADR 0333 captions leftover-map comparison leftover-axis ticks with persisted leftover-map
axis share when leftoverMapCompareAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption. Distinct accessible names
`leftover map comparison leftover axis {axis} tick {value} {share}%` and
`leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%`.
Share and singular value omit independently. Rank-0 unused axes still name leftover-map
comparison leftover-axis tick leftover-map axis share `0%`. Do not invent leftover-map
axis share from leftover-map singular values. Do not invent leftover-map singular values from leftover-map
axis share. Leftover-axis ticks never name leftover-map axis share this increment.
ADR 0334 captions leftover-axis ticks with persisted leftover-map
axis share when leftoverMapAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption. Distinct accessible names
`leftover axis {axis} tick {value} {share}%` and
`leftover axis {axis} tick {value} σ {singular} {share}%`.
Share and singular value omit independently. Rank-0 unused axes still name leftover-map
leftover-axis tick leftover-map axis share `0%`. Do not invent leftover-map
axis share from leftover-map singular values. Do not invent leftover-map singular values from leftover-map
axis share.
ADR 0335 captions leftover-map graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapPlotCriterionBadge returns a usable leftover-map criterion leftover-map
item coordinate caption. Distinct accessible name
`leftover-map criterion {label} at ζ {item}`.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map criterion leftover-map
item coordinate caption and keeps `Criterion ζ {label}`. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Do not invent leftover-map item coordinates from leftover-map post
`ξ`. Do not invent leftover-map post `ξ` from leftover-map item coordinates. Leftover-map comparison graphic leftover-map
criterion markers never name leftover-map item coordinates this increment.
ADR 0336 captions leftover-map comparison graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapComparePlotCriterionBadge returns a usable leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate caption. Distinct accessible name
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate caption and keeps `Criterion ζ {label}`. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Do not invent leftover-map item coordinates from leftover-map post
`ξ`. Do not invent leftover-map post `ξ` from leftover-map item coordinates. Leftover-map graphic leftover-map
criterion markers stay `leftover-map criterion {label} at ζ {item}` this increment.
ADR 0337 captions leftover-map comparison graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapComparePlotPostBadge returns a usable leftover-map comparison graphic leftover-map post leftover-map
person coordinate caption. Distinct accessible name
`Open leftover map comparison graphic leftover-map post {title} at ξ {person}`.
A missing or non-finite leftover-map person coordinate pair omits that leftover-map comparison graphic leftover-map post leftover-map
person coordinate caption and keeps `Open leftover-map post {title}`. Rank-0 unused axes still name leftover-map
person coordinates `(0.00, 0.00)`. Do not invent leftover-map person coordinates from leftover-map item coordinates
`ζ`. Do not invent leftover-map item coordinates `ζ` from leftover-map person coordinates `ξ`. Leftover-map graphic leftover-map
post markers stay `Open leftover-map post {title} at ξ {person}` this increment.
ADR 0338 captions leftover-map graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapPlotPostBadge returns a usable leftover-map graphic leftover-map post leftover-map
person coordinate caption. Distinct accessible name
`Open leftover-map post {title} at ξ {person}`.
A missing or non-finite leftover-map person coordinate pair omits that leftover-map graphic leftover-map post leftover-map
person coordinate caption and keeps `Open leftover-map post {title}`. Rank-0 unused axes still name leftover-map
person coordinates `(0.00, 0.00)`. Do not invent leftover-map person coordinates from leftover-map item coordinates
`ζ`. Do not invent leftover-map item coordinates `ζ` from leftover-map person coordinates `ξ`. Leftover-map comparison graphic leftover-map
post markers stay `Open leftover map comparison graphic leftover-map post {title} at ξ {person}` this increment.
ADR 0339 captions leftover-map pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapListPostBadge returns a usable leftover-map pair leftover-map post leftover-map
person coordinate caption. Distinct accessible name
`leftover pair leftover-map post {title} at ξ {person}`.
A missing or non-finite leftover-map person coordinate pair omits that leftover-map pair leftover-map post leftover-map
person coordinate caption and keeps `Open leftover {kind} pair: {title} · {criterion}`. Rank-0 unused axes still name leftover-map
person coordinates `(0.00, 0.00)`. Do not invent leftover-map person coordinates from leftover-map item coordinates
`ζ`. Do not invent leftover-map item coordinates `ζ` from leftover-map person coordinates `ξ`. Leftover-map graphic leftover-map
post markers stay `Open leftover-map post {title} at ξ {person}` this increment. Leftover-map comparison graphic leftover-map
post markers stay `Open leftover map comparison graphic leftover-map post {title} at ξ {person}` this increment.
ADR 0340 captions leftover-map pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapListCriterionBadge returns a usable leftover-map pair leftover-map criterion leftover-map
item coordinate caption. Distinct accessible name
`leftover pair leftover-map criterion {label} at ζ {item}`.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map pair leftover-map criterion leftover-map
item coordinate caption. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Do not invent leftover-map item coordinates from leftover-map person coordinates
`ξ`. Do not invent leftover-map person coordinates `ξ` from leftover-map item coordinates `ζ`. Leftover-map pair leftover-map
post leftover-map person coordinates stay `leftover pair leftover-map post {title} at ξ {person}` this increment. Leftover-map graphic leftover-map
criterion markers stay `leftover-map criterion {label} at ζ {item}` this increment. Leftover-map comparison graphic leftover-map
criterion markers stay `leftover map comparison graphic leftover-map criterion {label} at ζ {item}` this increment.
ADR 0341 captions leftover-map comparison leftover-pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapCompareListPostBadge returns a usable leftover-map comparison leftover-pair leftover-map post leftover-map
person coordinate caption. Distinct accessible name
`leftover map comparison leftover pair leftover-map post {title} at ξ {person}`.
A missing or non-finite leftover-map person coordinate pair omits that leftover-map comparison leftover-pair leftover-map post leftover-map
person coordinate caption and keeps `Open leftover {kind} pair from comparison: {title} · {criterion}`. Rank-0 unused axes still name leftover-map
person coordinates `(0.00, 0.00)`. Do not invent leftover-map person coordinates from leftover-map item coordinates
`ζ`. Do not invent leftover-map item coordinates `ζ` from leftover-map person coordinates `ξ`. Leftover-map pair leftover-map
post leftover-map person coordinates stay `leftover pair leftover-map post {title} at ξ {person}` this increment. Leftover-map graphic leftover-map
post markers stay `Open leftover-map post {title} at ξ {person}` this increment. Leftover-map comparison graphic leftover-map
post markers stay `Open leftover map comparison graphic leftover-map post {title} at ξ {person}` this increment.
ADR 0342 captions leftover-map comparison leftover-pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapCompareListCriterionBadge returns a usable leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinate caption. Distinct accessible name
`leftover map comparison leftover pair leftover-map criterion {label} at ζ {item}`.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinate caption. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Do not invent leftover-map item coordinates from leftover-map person coordinates
`ξ`. Do not invent leftover-map person coordinates `ξ` from leftover-map item coordinates `ζ`. Leftover-map comparison leftover-pair leftover-map
post leftover-map person coordinates stay `leftover map comparison leftover pair leftover-map post {title} at ξ {person}` this increment. Leftover-map pair leftover-map
criterion leftover-map item coordinates stay `leftover pair leftover-map criterion {label} at ζ {item}` this increment. Leftover-map graphic leftover-map
criterion markers stay `leftover-map criterion {label} at ζ {item}` this increment. Leftover-map comparison graphic leftover-map
criterion markers stay `leftover map comparison graphic leftover-map criterion {label} at ζ {item}` this increment.
ADR 0343 captions leftover-map graphic leftover-map axis origin ticks with leftover-map origin when leftoverMapPlotTickAxisBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values. Distinct accessible name
`leftover-map axis {axis} origin tick {value}`. Rank-0 unused axes still name leftover-map origin `0.00`. Share and singular omit independently.
Do not invent leftover-map origin from leftover-map axis share or leftover-map singular values `σ_k`. leftoverMapComparePlotTickAxisBadge stays
`leftover map comparison graphic leftover-map axis {axis} tick {value}` this increment.
ADR 0344 captions leftover-map comparison graphic leftover-map axis origin ticks with leftover-map origin when leftoverMapComparePlotTickAxisBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values. Distinct accessible name
`leftover map comparison graphic leftover-map axis {axis} origin tick {value}`. Rank-0 unused axes still name leftover-map origin `0.00`. Share and singular omit independently.
Do not invent leftover-map origin from leftover-map axis share or leftover-map singular values `σ_k`. leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map
axis origin tick keys. leftoverMapCompareAxisTickBadge and leftoverMapAxisTickBadge stay leftover-map tick keys this increment.
ADR 0345 captions leftover-map comparison leftover-axis origin ticks with leftover-map origin when leftoverMapCompareAxisTickBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values. Distinct accessible name
`leftover map comparison leftover axis {axis} origin tick {value}`. Rank-0 unused axes still name leftover-map origin `0.00`. Share and singular omit independently.
Do not invent leftover-map origin from leftover-map axis share or leftover-map singular values `σ_k`. leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map
axis origin tick keys. leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys. leftoverMapAxisTickBadge stays leftover-map tick keys this increment.
ADR 0346 captions leftover-map leftover-axis origin ticks with leftover-map origin when leftoverMapAxisTickBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values. Distinct accessible name
`leftover axis {axis} origin tick {value}`. Rank-0 unused axes still name leftover-map origin `0.00`. Share and singular omit independently.
Do not invent leftover-map origin from leftover-map axis share or leftover-map singular values `σ_k`. leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map
axis origin tick keys. leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys. leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys this increment.
ADR 0347 captions leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates with leftover-map origin when leftoverMapPlotCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map person coordinates. Distinct accessible name
`leftover-map criterion {label} at leftover-map origin ζ {item}`. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
Do not invent leftover-map origin from leftover-map person coordinates `ξ`. leftoverMapComparePlotCriterionBadge stays leftover-map comparison graphic leftover-map
criterion leftover-map item coordinate keys. leftoverMapPlotPostBadge stays leftover-map graphic leftover-map post leftover-map person coordinate keys this increment.
ADR 0348 captions leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates with leftover-map origin when leftoverMapPlotPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map criterion leftover-map item coordinates. Distinct accessible name
`Open leftover-map post {title} at leftover-map origin ξ {person}`. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
Do not invent leftover-map origin from leftover-map item coordinates `ζ`. leftoverMapComparePlotPostBadge stays leftover-map comparison graphic leftover-map
post leftover-map person coordinate keys. leftoverMapPlotCriterionBadge stays leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinate keys this increment.
ADR 0349 captions leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates with leftover-map origin when leftoverMapComparePlotPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates. Distinct accessible name
`Open leftover map comparison graphic leftover-map post {title} at leftover-map origin ξ {person}`. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
Do not invent leftover-map origin from leftover-map item coordinates `ζ`. leftoverMapPlotPostBadge stays leftover-map graphic leftover-map
post leftover-map origin leftover-map person coordinate keys. leftoverMapComparePlotCriterionBadge stays leftover-map comparison graphic leftover-map criterion leftover-map item coordinate keys this increment.
ADR 0350 captions leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinates with leftover-map origin when leftoverMapComparePlotCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates. Distinct accessible name
`leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}`. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
Do not invent leftover-map origin from leftover-map person coordinates `ξ`. leftoverMapPlotCriterionBadge stays leftover-map graphic leftover-map
criterion leftover-map origin leftover-map item coordinate keys. leftoverMapComparePlotPostBadge stays leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinate keys this increment.
When `R`, `R̂`, `U`, `x`,
`s`, and `e` are finite, `e + s + x = 1`. When `Y`, `E`, and `R` are
finite, `Y − E = R`. When `R`, `R̂`, and `U` are
finite, `U + R̂ = R`. When coordinates,
reconstruction, and distance are finite, `R̂ = ξ · ζ` and
`d = ‖ξ − ζ‖`. The pairs sit above the member
list so a click opens that post with the leftover criterion current
in Post quality (ADR 0158). Leftover-map axis share (ADR 0148) is Gabriel inertia of
residual SVD axes 1 and 2 and persists to `report_leftover_map_axis`.
Rank-0 residuals emit two zero-share axes; the shares are report-level
and are not a leftover score. Complete-case coverage (ADR 0168) persists to
`report_leftover_map_coverage` and captions the pair list and the leftover-map
graphic with how many scored posts entered the map. Pair-list post complete-case
coverage (ADR 0288) fail-closes that pair-list note through leftoverMapCoverageCounts.
Grouping comparison complete-case coverage (ADR 0289) captions the grouping
comparison strip with how many scored posts entered each grouping's map.
Grouping comparison item complete-case coverage (ADR 0290) captions the grouping
comparison strip with how many scored criteria entered each grouping's map.
Grouping comparison incomplete post coverage (ADR 0291) captions the grouping
comparison strip with how many scored posts stayed out of each grouping's map.
Grouping comparison incomplete item coverage (ADR 0292) captions the grouping
comparison strip with how many scored criteria stayed out of each grouping's map.
Grouping comparison reconstruction (ADR 0293) captions grouping comparison leftover-pair
buttons with persisted leftover-map reconstruction `R̂`.
Grouping comparison explained leftover share (ADR 0294) captions grouping comparison leftover-pair
buttons with persisted leftover-map explained leftover share `e`.
Grouping comparison unexplained leftover share (ADR 0295) captions grouping comparison leftover-pair
buttons with persisted leftover-map unexplained leftover share `s`.
Grouping comparison leftover-map cross share (ADR 0296) captions grouping comparison leftover-pair
buttons with persisted leftover-map cross share `x`.
Grouping comparison leftover-map unexplained leftover (ADR 0297) captions grouping comparison leftover-pair
buttons with persisted leftover-map unexplained leftover `U`.
Grouping comparison leftover residual (ADR 0298) captions grouping comparison leftover-pair
buttons with persisted leftover residual `R`.
Grouping comparison leftover observed (ADR 0299) captions grouping comparison leftover-pair
buttons with persisted leftover observed `Y`.
Grouping comparison leftover expected (ADR 0300) captions grouping comparison leftover-pair
buttons with persisted leftover expected `E`.
Grouping comparison leftover-map rank (ADR 0301) captions grouping comparison leftover-pair
buttons with persisted leftover-map rank.
Grouping comparison leftover-map coordinates (ADR 0302) captions grouping comparison leftover-pair
buttons with persisted leftover-map coordinates `ξ` / `ζ`.
Grouping comparison leftover-map coordinates payload (ADR 0303) returns persisted leftover-map
coordinates `ξ` / `ζ` on `GET /api/reports/compare/{period}` leftover pairs.
Grouping comparison leftover-map graphic display (ADR 0304) draws the leftover-map
graphic of those already-named coordinates above grouping comparison leftover-pair
buttons when four leftover-map axes are finite.
Grouping comparison leftover-map axis share (ADR 0305) captions that grouping
comparison leftover-map graphic with persisted leftover-map axis share.
Grouping comparison leftover-map complete-case coverage (ADR 0306) captions that
grouping comparison leftover-map graphic with persisted leftover-map complete-case
coverage when leftoverMapCoverageCounts returns usable complete-case integers.
Grouping comparison leftover-map item complete-case coverage (ADR 0307) captions
that grouping comparison leftover-map graphic with persisted leftover-map item
complete-case coverage when leftoverMapItemCoverageCounts returns usable
complete-case integers.
Grouping comparison leftover-map incomplete post coverage (ADR 0308) captions
that grouping comparison leftover-map graphic with persisted leftover-map incomplete
post coverage when leftoverMapIncompletePostCount returns a usable dropped integer.
Grouping comparison leftover-map incomplete item coverage (ADR 0309) captions
that grouping comparison leftover-map graphic with persisted leftover-map incomplete
item coverage when leftoverMapIncompleteItemCount returns a usable dropped integer.
Grouping comparison leftover-map reconstruction (ADR 0310) captions
that grouping comparison leftover-map graphic with persisted leftover-map reconstruction
`R̂` when formatLeftoverMapReconstruction returns a usable signed badge.
Grouping comparison leftover-map explained leftover share (ADR 0311) captions
that grouping comparison leftover-map graphic with persisted leftover-map explained leftover
share `e` when formatLeftoverMapExplainedShare returns a usable badge.
Grouping comparison leftover-map unexplained leftover share (ADR 0312) captions
that grouping comparison leftover-map graphic with persisted leftover-map unexplained leftover
share `s` when formatLeftoverMapUnexplainedShare returns a usable badge.
Grouping comparison leftover-map cross share (ADR 0313) captions
that grouping comparison leftover-map graphic with persisted leftover-map cross
share `x` when formatLeftoverMapCrossShare returns a usable badge.
Grouping comparison leftover-map unexplained leftover (ADR 0314) captions
that grouping comparison leftover-map graphic with persisted leftover-map unexplained leftover
`U` when formatLeftoverMapUnexplained returns a usable badge.
Grouping comparison leftover residual (ADR 0315) captions
that grouping comparison leftover-map graphic with persisted leftover residual
`R` when formatLeftoverMapResidual returns a usable badge.
Grouping comparison leftover observed (ADR 0316) captions
that grouping comparison leftover-map graphic with persisted leftover observed
`Y` when formatLeftoverMapObserved returns a usable badge.
Grouping comparison leftover expected (ADR 0317) captions
that grouping comparison leftover-map graphic with persisted leftover expected
`E` when formatLeftoverMapExpected returns a usable badge.
Grouping comparison leftover-map rank (ADR 0318) captions
that grouping comparison leftover-map graphic with persisted leftover-map rank
when formatLeftoverMapRank returns a usable badge.
Grouping comparison leftover-map distance (ADR 0319) captions
that grouping comparison leftover-map graphic with persisted leftover-map distance
`d` when formatLeftoverMapDistance returns a usable badge.
Grouping comparison leftover-map coordinate ticks (ADR 0320) captions
that grouping comparison leftover-map graphic with persisted leftover-map coordinate
ticks at the origin and at each unique finite `ξ` / `ζ` projection.
Grouping comparison leftover-map singular values (ADR 0321) captions
that grouping comparison leftover-map graphic with persisted leftover-map singular
values `σ_k` when leftoverSingularForAxis returns a usable finite non-negative value.
Leftover-axis report badge leftover-map singular values (ADR 0322) captions leftover-axis
report badges with persisted leftover-map singular values `σ_k` when leftoverMapAxisBadgeSingular
returns a usable finite non-negative value.
Grouping comparison leftover-axis report badge leftover-map singular values (ADR 0323) captions
leftover-axis report badges on the grouping comparison strip with persisted leftover-map
singular values `σ_k` when leftoverMapCompareAxisBadge returns a usable leftover-axis caption.
Leftover-map graphic-display leftover-map singular values (ADR 0324) captions leftover-map
graphic-display axes with persisted leftover-map singular values `σ_k` when leftoverMapPlotAxisBadge
returns a usable leftover-map axis caption.
Leftover-axis report badge leftover-map singular values independently of leftover-map axis share
(ADR 0325) captions leftover-axis report badges with persisted leftover-map singular values
`σ_k` when leftoverMapAxisBadge returns a usable leftover-axis caption.
Leftover-map comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
(ADR 0326) captions leftover-map comparison graphic leftover-map axes with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotAxisBadge returns a usable leftover-map axis caption.
Leftover-map graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0327) captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapPlotTickAxisBadge returns a usable leftover-map axis tick caption.
Leftover-map comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0328) captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map axis tick caption.
Leftover-map comparison leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0329) captions leftover-map comparison leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapCompareAxisTickBadge returns a usable leftover-axis tick caption.
Leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0330) captions leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapAxisTickBadge returns a usable leftover-axis tick caption.
Leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0331) captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption.
Leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0332) captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapPlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption.
Leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0333) captions leftover-map comparison leftover-axis ticks with persisted leftover-map
axis share when leftoverMapCompareAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption.
Leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0334) captions leftover-axis ticks with persisted leftover-map
axis share when leftoverMapAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption.
Leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(ADR 0335) captions leftover-map graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapPlotCriterionBadge returns a usable leftover-map criterion leftover-map
item coordinate caption.
Leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(ADR 0336) captions leftover-map comparison graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapComparePlotCriterionBadge returns a usable leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate caption.
Leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
(ADR 0337) captions leftover-map comparison graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapComparePlotPostBadge returns a usable leftover-map comparison graphic leftover-map post leftover-map
person coordinate caption.
Leftover-map graphic leftover-map post leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post markers
(ADR 0338) captions leftover-map graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapPlotPostBadge returns a usable leftover-map graphic leftover-map post leftover-map
person coordinate caption.
Leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates
(ADR 0339) captions leftover-map pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapListPostBadge returns a usable leftover-map pair leftover-map post leftover-map
person coordinate caption.
Leftover-map pair leftover-map criterion leftover-map item coordinates independently of leftover-map pair leftover-map post leftover-map person coordinates
(ADR 0340) captions leftover-map pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapListCriterionBadge returns a usable leftover-map pair leftover-map criterion leftover-map
item coordinate caption.
Leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates
(ADR 0341) captions leftover-map comparison leftover-pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapCompareListPostBadge returns a usable leftover-map comparison leftover-pair leftover-map post leftover-map
person coordinate caption.
Leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates
(ADR 0342) captions leftover-map comparison leftover-pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapCompareListCriterionBadge returns a usable leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinate caption.
Leftover-map graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
(ADR 0343) captions leftover-map graphic leftover-map axis origin ticks when leftoverMapPlotTickAxisBadge returns a leftover-map origin tick caption.
Leftover-map comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
(ADR 0344) captions leftover-map comparison graphic leftover-map axis origin ticks when leftoverMapComparePlotTickAxisBadge returns a leftover-map origin tick caption.
Leftover-map comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
(ADR 0345) captions leftover-map comparison leftover-axis origin ticks when leftoverMapCompareAxisTickBadge returns a leftover-map origin tick caption.
Leftover-map leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
(ADR 0346) captions leftover-map leftover-axis origin ticks when leftoverMapAxisTickBadge returns a leftover-map origin tick caption.
Leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map person coordinates
(ADR 0347) captions leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapPlotCriterionBadge returns a leftover-map origin leftover-map item coordinate caption.
Leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
(ADR 0348) captions leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapPlotPostBadge returns a leftover-map origin leftover-map person coordinate caption.
Leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates
(ADR 0349) captions leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapComparePlotPostBadge returns a leftover-map origin leftover-map person coordinate caption.
Leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates
(ADR 0350) captions leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapComparePlotCriterionBadge returns a leftover-map origin leftover-map item coordinate caption.
Item complete-case coverage
(ADR 0282) captions the leftover-map graphic with how many scored criteria
entered the map. Item complete-case coverage on the pair list (ADR 0285)
captions the pair list with how many scored criteria entered the map. Incomplete post coverage (ADR 0283) captions the leftover-map
graphic with how many scored posts stayed out of the factorization. Incomplete
post coverage on the pair list (ADR 0286) captions the pair list with how many
scored posts stayed out of the factorization. Incomplete
item coverage (ADR 0284) captions the leftover-map graphic with how many
scored criteria stayed out of the factorization. Incomplete
item coverage on the pair list (ADR 0287) captions the pair list with how many
scored criteria stayed out of the factorization.

Authorized occupational construct catalog search (ADR 0257) matches official
O*NET preferred labels or descriptions only when a source-eligible, ABAC-visible
Post supports that construct. Hidden Posts, withdrawn truth, and conflicting
truth statuses omit the hit. Clicking a hit opens that Post. Do not return
catalog rows as a vocabulary oracle, scores, or person traits. Continuation
is a construct-IRI keyset; never OFFSET.

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
`docs/storybook-inventory.md`. Success, unavailable, and retry copy share
`StatusNotice` (ADR 0220): Calendar's missing Naruon projection is the first
migrated flow. Success and unavailable stay a named region (not live
`role="status"`); retry stays `role="alert"`. Do not add a second placeholder
or interpolate provider payloads into that notice.

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
Global Ask uses the same revision cover when `knowledge_cutoff` is set
(ADR 0216 / #271); omit the field to keep the live-query contract, and
never substitute a live body for a missing historical cover.

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

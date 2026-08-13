# Architecture

## Scope and non-scope

LineageWeave reconstructs a plausible thread structure over records that
already exist somewhere else. It does not ingest, own, or persist any
source-of-truth data, and it does not perform calibrated statistical
estimation. Both of those are explicitly out of scope and pushed to other
repos in the ecosystem:

- **Ingestion** of raw exports into governed tables is
  [mhtml-etl-gateway](https://github.com/ContextualWisdomLab/mhtml-etl-gateway)'s
  job.
- **Calibrated psychometric/temporal measurement** (latent trait scores,
  trajectories, uncertainty-quantified estimates) is
  [TEPP](https://github.com/ContextualWisdomLab/TEPP)'s job.

This is why the org-wide rule that mathematical/psychometrics computation
layers must be Rust with GPU + CPU multithreading does not apply to this
repo: LineageWeave does no such computation. Its heaviest per-request work
is fusing a handful of `[0, 1]` channel scores over a bounded candidate
window (`reconstruct.DEFAULT_CANDIDATE_WINDOW`, default 50) -- a scheduling
and orchestration problem, not a numerical-estimation one. If a future
version added real statistical inference (e.g. estimating thread-assignment
uncertainty), that layer would move into TEPP rather than being built here,
consistent with the dependency direction the ecosystem's own architecture
docs already establish (`psychometrics-commons`'s TRD explicitly forbids a
downstream product from reimplementing a measurement engine's model).

## Data flow

```mermaid
flowchart LR
    subgraph Source
        R[Records<br/>id, group_key, label,<br/>occurred_at, secondary_key]
    end

    subgraph LineageWeave
        G[Group by group_key]
        C[Candidate window<br/>most recent N priors]
        CH[Channels<br/>temporal · secondary_key · text · llm]
        F[RankWeave<br/>weighted_convex_fuse]
        T[ThreadWeave<br/>thread_messages]
    end

    subgraph External services, all optional
        EMB[Embedding provider<br/>swap in for the text channel]
        ORC[contextual-orchestrator<br/>mode=verify, llm channel]
        TEPP[TEPP<br/>AnalysisRunRequest v1,<br/>calibrated measurement]
    end

    R --> G --> C --> CH --> F --> T --> OUT[Tree per group:<br/>roots, edges, branch points]
    CH -.text channel.-> EMB
    CH -.llm channel.-> ORC
    OUT -.optional export.-> TEPP
```

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | `Record`, `Edge`, `Tree` -- source-agnostic data shapes |
| `channels.py` | Independent `[0, 1]` scoring functions |
| `embedding_client.py` | Pluggable text-embedding channel (`Null` default, `OpenAiCompatible` real impl) |
| `adjudication_client.py` | Pluggable LLM-judgment channel (`Null` default, `ContextualOrchestrator` real impl) |
| `tepp_client.py` | TEPP's published `AnalysisRunRequest` wire contract, pluggable transport |
| `reconstruct.py` | The pipeline: group → candidate window → score → fuse → thread |
| `fixtures.py` | Synthetic demo dataset -- no real data ships in this repo |
| `server.py` | Stdlib HTTP server: `GET /api/lineage` (JSON graph) + static viewer |
| `web/index.html` | Self-contained SVG DAG viewer, no build step, no external script dependency |

## Design decisions worth naming

- **Pluggable, never faked, channels.** `NullEmbeddingClient` and
  `NullAdjudicationClient` make a channel *unavailable* (dropped and
  renormalized in `active_weights()`), never silently scored as 0. A
  missing signal and a confidently-negative signal are different things and
  must not be conflated.
- **A minimum fused-score floor** (`DEFAULT_MIN_FUSED_SCORE`). Without it,
  every record after the first in a group gets *some* parent even when
  every candidate is a weak match -- wrong more often than useful. See
  `fixtures.sample_records()`'s intentionally-unrelated `rec-006` and its
  test in `tests/test_reconstruct.py`.
- **A bounded candidate window** (`DEFAULT_CANDIDATE_WINDOW`, default 50).
  `ponytail`-tagged in `reconstruct.py`: keeps per-group cost `O(n * window)`
  instead of `O(n^2)` for large groups; raise it if recall against a labeled
  set ever shows true parents falling outside the window.
- **TEPP is a wire contract, not an import.** `tepp_client.py`'s default
  transport raises `TeppNotAvailable` rather than silently no-op'ing,
  because TEPP has no live HTTP endpoint yet; the shape is validated
  (`AnalysisRunRequest.to_json()` mirrors TEPP's published JSON Schema
  exactly, `additionalProperties: false` and all) so wiring in a real
  transport is additive, not a rewrite.

## Standards and citations

See [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md)
for the full APA 7th reference list this design is grounded in.

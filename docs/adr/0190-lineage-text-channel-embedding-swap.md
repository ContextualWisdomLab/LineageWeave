# ADR 0190: Swap the lineage `text` channel to real embeddings when available

- Status: Accepted
- Date: 2026-08-24

## Context

A reader reported Event Lineage entangling topically and causally unrelated
posts. Root-caused against a live corpus (not a hypothetical): the reported
post's `thread_group_key` and `secondary_grouping_key` were both empty, so
`reconstruct_group_key` (`backend/app/lineage_ingestion.py`) fell back to
`process_unit_id` -- an entire team's inbox, over 21,000 posts spanning
three-plus years, not a thread. That coarse-group fallback is intentional,
documented design (it must match `GET /api/lineage`'s own display grouping;
see ADR 0064, ADR 0143) and is out of scope here.

Within that group, `reconstruct()`'s `DEFAULT_CANDIDATE_WINDOW` (50
temporally-preceding records) drew candidates from a topically unbounded
pool, and the `text` channel -- `lineageweave/channels.py`'s
`text_similarity_score` -- is `difflib.SequenceMatcher` character overlap on
raw titles, a channel the module's own docstring already named as a
temporary stand-in ("swap in `EmbeddingClient` + cosine similarity ... once
an embedding provider is configured"). With no `AdjudicationClient`
configured for the corpus-wide rebuild path (a separate, independently
tracked gap), the `llm` channel drops out and `temporal`/`secondary_key`/
`text` renormalize to 0.25/0.25/0.50 (`active_weights`,
`DEFAULT_CHANNEL_WEIGHTS`). Two short titles that happen to share common
words or sentence structure -- e.g. two differently-topiced status updates
with the same subject/verb shape -- can clear a 0.8+ difflib ratio despite
being about unrelated topics; combined with temporal proximity, that alone
clears `DEFAULT_MIN_FUSED_SCORE` (0.3) and produces a spurious parent-child
edge. `tests/test_reconstruct.py::test_embedding_channel_overrides_a_difflib_false_positive`
reproduces this synthetically and asserts the fix.

This environment already has `LLM_GATEWAY_EMBEDDING_MODEL` configured and
`lineageweave.embedding_client.ContextualOrchestratorEmbeddingClient` already
in production use for post-content search embeddings
(`lineageweave/post_content_persistence.py`) -- the embedding channel this
ADR wires was staged capability, not new infrastructure.

## Decision

- `reconstruct()` gains an `embedding: EmbeddingClient | None = None`
  parameter, mirroring `llm`'s existing shape: `None` maps to
  `NullEmbeddingClient` (channel absent, never faked), matching ADR 0064's
  "a missing channel is dropped ... it is never replaced with a fabricated
  score" rule.
- Unlike `llm` (a genuine per-candidate-pair judgment), embeddings are
  precomputed **once per reconstruction**, batched, before scoring begins --
  `_embed_labels` embeds every input record's label up front (bounded
  batches, same 64-record/24,000-character philosophy as
  `post_content_persistence.py`'s LLM batching) into a `record_id -> vector`
  map. `_best_parent` then scores the `text` channel as
  `cosine_similarity(candidate_vector, record_vector)` when both records
  have a vector, falling back to `text_similarity_score`'s difflib ratio
  otherwise (a missing vector -- e.g. one failed batch -- degrades that pair
  back to the pre-embedding behavior, not to a fabricated score or a hard
  failure).
- The `text` channel key, its 0.30 weight, and the fusion code in
  `reconstruct.py` are unchanged -- only the score's *source* changes,
  exactly as the pre-existing docstring specified. No new channel, no weight
  rebalancing.
- `embedding` is threaded through the same call chain `llm` already uses:
  `lineage_edge_specs` (`lineageweave/lineage_persistence.py`) ->
  `rebuild_lineage` (`backend/app/lineage_ingestion.py`) ->
  `deliver_queued_analysis_run`/`_deliver_lineage_reconstruction`
  (`backend/app/analysis_run_start.py`) ->
  `consume_analysis_run_stream_once`/`run_analysis_run_worker`
  (`backend/app/analysis_run_worker.py`) -> `backend/app/main.py`'s
  `lifespan()` worker task, `POST /api/lineage/rebuild`, and the
  analysis-run start endpoint, all now passing the existing
  `_embedding_client()` factory alongside `_adjudication_client()`.
  `scripts/import_postgresql_posts.py` passes the `embedding_client` it
  already builds for post-content embedding into `rebuild_lineage` too.

## Amendment (2026-08-24): clamp, don't remap, the raw cosine

Post-review finding (Devin Review on this PR): the initial implementation
mapped `cosine_similarity`'s output via `(cosine + 1) / 2`, the textbook
transform for a similarity measure that spans the full `[-1, 1]` range. Real
sentence embeddings do not: they occupy an anisotropic cone (Ethayarajh,
2019), so two genuinely unrelated short texts from an actual provider score
a modestly *positive* raw cosine in practice, essentially never near -1. The
remap inflated that unrelated baseline to roughly 0.5-0.65 -- a "weak
positive" channel score that, combined with any temporal proximity, could
still clear `DEFAULT_MIN_FUSED_SCORE` and reproduce the exact false-positive
edge this ADR set out to close, just through the embedding channel instead
of difflib. Fixed by clamping the raw cosine into `[0, 1]`
(`max(0.0, min(1.0, cosine))`) instead of remapping it, matching how cosine
similarity is used unremapped in the STS evaluation convention (Reimers &
Gurevych, 2019) already cited above.

This also surfaced a distinct, still-open observation worth flagging rather
than silently absorbing into this fix: for two records roughly an hour
apart, `temporal_score` alone (`1 / (1 + gap_days)`) already contributes
close to `DEFAULT_MIN_FUSED_SCORE` on its own once weights renormalize
without an `llm` channel, so *any* weakly-positive text score -- clamped
cosine included -- can still tip a temporally-close, topically-unrelated
pair over the floor. Flagged here rather than in
`docs/product-technical-gap-baseline.md` -- this branch predates that
document's current structure; carry this observation forward on the next
rebase against `main`. Changing `temporal_score`'s steepness or
`DEFAULT_MIN_FUSED_SCORE` is a calibration decision outside this PR's scope.

## Consequences

- When an embedding provider is configured (already true in this
  environment), Event Lineage edges within a large, coarsely-grouped bucket
  are judged on semantic similarity instead of character overlap, directly
  reducing the reported entanglement failure mode.
- No behavior change when no embedding provider is configured -- the
  `text` channel is exactly what it was before this ADR (difflib), so this
  is a pure addition, not a breaking change to any environment without
  `LLM_GATEWAY_EMBEDDING_MODEL` set.
- A corpus-wide rebuild now makes one batched embedding call per
  `_EMBEDDING_BATCH_MAX_RECORDS` (64) records in addition to existing work,
  bounded and logged-through the same provider-failure handling pattern
  already established for post-content embedding (a failed batch is an
  absent signal, not an aborted rebuild).
- Does not address the separate, larger architectural question of whether
  `process_unit_id` should ever be the grouping fallback for a thread-shaped
  UI -- that decision needs its own ADR and is out of scope here (see
  `docs/product-technical-gap-baseline.md`). This ADR narrows how often a
  *wrong* group produces a *visibly wrong* edge; it does not shrink the
  group itself.
- Independent of, and does not duplicate, the separate open PR wiring
  `AdjudicationClient` into `rebuild_lineage()` (restores the `llm`
  channel's 0.40 weight for the corpus-wide rebuild path specifically) --
  that PR and this ADR fix two different channels of the same fusion and
  compose without conflict.

## References — APA 7th

Ethayarajh, K. (2019). How contextual are contextualized word
representations? Comparing the geometry of BERT, ELMo, and GPT-2 embeddings.
In *Proceedings of the 2019 Conference on Empirical Methods in Natural
Language Processing and the 9th International Joint Conference on Natural
Language Processing (EMNLP-IJCNLP)* (pp. 55-65). Association for
Computational Linguistics. https://doi.org/10.18653/v1/D19-1006

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using
Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical
Methods in Natural Language Processing and the 9th International Joint
Conference on Natural Language Processing (EMNLP-IJCNLP)* (pp. 3982-3992).
Association for Computational Linguistics. https://doi.org/10.18653/v1/D19-1410

Christen, P. (2012). *Data matching: Concepts and techniques for record
linkage, entity resolution, and duplicate detection*. Springer.
https://doi.org/10.1007/978-3-642-31164-2

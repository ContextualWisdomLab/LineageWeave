# ADR 0107: Bounded asynchronous lineage rebuild with an optional LLM channel

- Status: Accepted
- Date: 2026-08-20
- Related: [0064](0064-lineage-evidence-and-tree-assembly.md),
  [0023](0023-analysis-run-outbox.md),
  [0098](0098-valkey-backed-post-content-ingestion.md)
- Refs: Issue #289

## Context

`reconstruct()` fuses temporal, secondary-key, text, and optional LLM
channels (Jeon et al., 2021, eq. 3 residual pairing is out of scope here;
this slice is RankWeave fusion plus ThreadWeave assembly per ADR 0064).
`lineage_edge_specs()` already accepts an `AdjudicationClient`. The live
`POST /api/lineage/rebuild` path ignored that client, so product
reconstructions silently used the three-channel fallback even when
contextual-orchestrator was configured.

Calling `judge()` synchronously inside the HTTP handler for every bounded
candidate pair would block the event loop, leave retry/idempotency
undefined, and mix a partial graph with a later run.

## Decision

1. `POST /api/lineage/rebuild` enqueues one `lineage_rebuild_job` row and
   returns that identity immediately. It does not call contextual-orchestrator
   on the request path.
2. PostgreSQL is the durable ledger. Valkey stream `lineage-rebuild-outbox`
   carries only the job id as a wake-up. A worker claims the row, runs
   `lineage_edge_specs` in `asyncio.to_thread`, and persists the full graph
   in one transaction.
3. The LLM channel is requested only through contextual-orchestrator. A
   missing, over-limit, skipped, or failed channel is recorded as
   unavailable / skipped / failed. Absence is never stored as score `0`.
4. Candidate-pair estimate uses the same window as `reconstruct()`. When
   the estimate exceeds `pair_limit`, the worker skips the LLM channel and
   completes the explicit three-channel degraded path.
5. Duplicate active jobs for the same snapshot digest and LLM-request flag
   reuse the existing row. A second delivery of a succeeded job does not
   call the provider or rewrite the graph.
6. Provider failure falls back to a complete deterministic reconstruct in
   the same job, then persists once. No mixed-run partial graph is visible.
7. Analysis-run start (ADR 0021 / 0023) remains a cutoff-bound registry
   path. This ADR owns the corpus-wide Event Lineage rebuild.

No TEPP theta, fast-mlsirm score, or raw provider call is introduced.

## Consequences

- A configured orchestrator is no longer silently ignored.
- HTTP stays responsive while model-backed work runs outside the event loop.
- Buyers can tell requested, available, completed, skipped, failed, and
  unavailable LLM-channel states apart and take the named next action.
- Historic fused scores are not rewritten except by a completed rebuild.

## References — APA 7th

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns:
Designing, building, and deploying messaging solutions*. Addison-Wesley.

Jeon, J.-J., Ryoo, J., & Lee, S. (2021). *Latent space item response model
for network data* (arXiv:2007.08719). https://doi.org/10.48550/arXiv.2007.08719

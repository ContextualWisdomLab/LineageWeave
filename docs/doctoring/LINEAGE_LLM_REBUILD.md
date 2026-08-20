# Event Lineage LLM rebuild (ADR 0100 / v2.22.0)

| Claim | Evidence |
| --- | --- |
| HTTP rebuild does not call contextual-orchestrator | `POST /api/lineage/rebuild` inserts `lineage_rebuild_job` and returns. `judge()` is not on that path. |
| A configured client is not ignored | The worker passes `_adjudication_client()` into `lineage_edge_specs` when the job status is requested/available. |
| Absence is not a zero score | Unavailable, skipped, and failed statuses drop the LLM channel via `NullAdjudicationClient`. |
| Duplicate delivery does not repeat provider work | Active snapshot+flag jobs are reused; a succeeded claim returns immediately. |
| Deterministic and model-backed runs are distinguishable | `llm_channel_status_code` plus `next_action` name the path. No TEPP theta is invented. |

# External Lineage Contract Traceability

| Requirement | Product decision | Implementation | Evidence |
|---|---|---|---|
| Caller authorization remains authoritative | Accept only caller-projected evidence and opaque references | `lineageweave.external_lineage_contract` | strict parser and hostile-input tests |
| Historical answers exclude future evidence | Filter by `available_at <= knowledge_cutoff` | `lineageweave.external_lineage_analysis` | cutoff inclusion/exclusion tests |
| RFC relations remain distinct | Explicit parent relations serialize as observed relation codes | execution adapter | observed-parent precedence tests |
| Semantic lineage remains inferred | Reconstructed edges use `truth_status_code=inferred` | execution adapter | result contract tests |
| Optional LLM absence is honest | Return `not_requested` or `unavailable`; do not fabricate a score | execution adapter | LLM policy tests |
| Work is bounded before provider calls | Enforce record count, candidate window, and maximum pair evaluations | parser and execution adapter | pair-budget tests |
| Project state is not silently mutated | Return only `proposed` project projections | contract/result validator | project truth-status tests |
| Consumer compatibility is machine-checkable | Publish JSON Schema and canonical request/result digests | schema and contract module | schema drift and digest tests |

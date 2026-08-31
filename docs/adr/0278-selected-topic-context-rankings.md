# ADR 0278: Selected topic-context Rankings

- Status: Accepted
- Date: 2026-08-31

## Decision

Rankings has no keyword or default lexical channel. An unselected read returns
only ABAC-visible persisted context choices. A ranking requires the exact
`topic_model_run_id`, `topic_influence_run_id`, `topic_index`,
`dimension_code`, and `context_id`; no value is maximized, pooled, copied, or
renormalized across contexts. The primary channel orders accepted persisted
`topic_post_context_influence.influence_value` evidence for that selection.
Newest-first may participate only over the identical selected membership
population. RankWeave owns exact Cormack fusion and its stopping certificate.

Migration 0268 adds maintained PostgreSQL access paths over the normalized
ADR 0210 tables. ABAC remains a source-post eligibility join before any row is
returned. The indexes contain no new fact and require no ontology term.

## Consequences

The endpoint cannot fabricate a ranking before the buyer selects one governed
topic and context. Missing producer evidence remains unavailable with an
actionable next step. ADR 0024's synthetic fixed-query lexical ranking is
retired; ADR 0167 contribution disclosure remains required.

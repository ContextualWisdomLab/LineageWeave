# ADR 0071: Post-scoped LLM session metadata

- Status: Accepted
- Date: 2026-08-19

## Decision

Every contextual-orchestrator request made about one post carries the same
deterministic `lineageweave_post_session_id` in the existing OpenAI-compatible
`metadata` object and, for POST requests, as the top-level orchestrator
`session_id`. The correlation header defined by ADR 0122 carries that same
value. The ID is derived from `post_id` with a LineageWeave-only UUID namespace;
it is not a database key and does not require a `user_account + post_id` table.
An explicitly supplied top-level value must equal the active post session;
the transport rejects a mismatch instead of silently splitting provenance.

The same metadata object carries non-body provenance hints when available:
PU, author account ID, corporate-entity code, and source author/company,
customer, project, and sales-pool codes. Raw title/body, credentials, and
provider-selected model names are not metadata.

`workflow_run_id` remains unique per LLM request for audit and cost accounting.
The post session ID groups related requests and is propagated natively by
contextual-orchestrator through normal Chat Completions, Responses-compatible
provider translation, streaming, and batch Embedding submission. It must not
be implemented by runtime monkey patching or by reusing a workflow run ID.

## Consequences

- Summary, Keyman, ontology/entity, Vision region/description, embedding,
  evaluation, chat, and commitment calls for one post can be correlated.
- Each request remains self-contained; the session ID is correlation context,
  not an implicit conversation-memory store.
- Posts without a post scope, such as global Ask Agent, do not receive a fake
  post session ID.
- Provider-neutral payloads sent to services other than contextual-orchestrator
  do not receive the orchestrator-only top-level `session_id` field.

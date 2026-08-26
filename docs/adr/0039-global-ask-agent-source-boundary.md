# ADR 0039: Global Ask Agent uses authorized evidence sources

- Status: Accepted
- Date: 2026-08-18

## Context

The buyer GNB requires an Ask Agent destination, but the existing UI only
opened post-scoped chat after the user selected a source post. That leaves the
buyer without a usable global question flow and risks treating an LLM lab
control as the product feature.

## Decision

`POST /api/ask` accepts a question and assembles a bounded source set from
`source_post` rows. Each row is rechecked with the requesting account's
`post_read` RBAC and post ABAC predicate before its normalized body enters the
context. Persisted Knowledge Graph facts and embedded image normalization use
the existing chat pipeline. Each Knowledge Graph fact remains attached only
to the visible source post recorded as its evidence; facts are never collected
under the first candidate merely because that post appears first in the prompt.
When a graph endpoint is itself a post, that endpoint must also belong to the
same authorized source window before its label can be hydrated. A visible
evidence post never makes a hidden or out-of-window endpoint post visible.
The answer is produced only by
`ContextualOrchestratorPostChatClient`, and citations resolve to the returned
source post ids and titles.

The frontend renders a question input, answer, and cited-post controls. A
cited post opens the Board detail through the same navigation state as every
other buyer evidence chip. Missing orchestrator or source evidence is an
explicit next action; the agent never fabricates an answer or citation.

## Consequences

- Ask Agent is a real buyer workflow rather than a required post selector.
- Authorization is enforced before LLM context assembly, not after the
  response.
- The initial context is bounded to 50 recent rows. Retrieval/reranking is a
  later upgrade if corpus size or prompt budget requires it.

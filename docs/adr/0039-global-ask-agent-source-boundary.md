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

## Proposed amendment: client observation lifetime (2026-09-07)

This amendment remains Proposed pending protected review. It does not change
the Accepted evidence-source decision above.

### Context and decision drivers

The client currently abandons a durable Ask job fifteen minutes after
submission, including queue wait. A synthetic deferred-status regression
reproduces abandonment after a queued job becomes running, before its next
succeeded response can be read. Elapsed observation time does not establish
provider failure. The requested model policy has no default application limit.

### Considered options and proposed outcome

Retaining or increasing the fixed ceiling bounds browser polling but still
rejects valid work solely because time elapsed. A second browser timeout setting
duplicates policy outside contextual-orchestrator. Instead, continue the existing
two-second polling until a terminal response, transport failure, or native
AbortSignal cancellation. Keep credential-generation admission checks for work
that already resolved when the screen was retired.

### Consequences and confirmation

The browser can observe late answers without resubmitting paid work. Polling can
continue indefinitely while a visible screen follows a stranded job; cancellation
on unmount or credential change still retires client I/O, not the server job.
The regression must advance past the former ceiling, observe a nonterminal
status, and then receive the actual completed answer. Existing cancellation
tests must continue passing without timer or listener leaks.

This is only the client observation decision. The backend's 600-second execution
deadline, answer socket limit, and 660-second age-based orphan recovery remain
an unresolved policy conflict. Removing execution limits requires a separate
worker-liveness and claim-fencing decision so recovery cannot duplicate a live
computation. Preserve ADR 0213's rule against holding pooled database connections
during provider work. No model administrator contract or end-to-end unlimited
execution is established by this amendment.

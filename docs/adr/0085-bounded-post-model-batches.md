# ADR 0085: Bounded post content model batches

- Status: Accepted
- Date: 2026-08-20
- Related: [0062](0062-semantic-unit-embedding.md), [0076](0076-paper-grounded-model-policy.md), [0084](0084-lineage-research-grounding.md)

## Context

The real corpus contains posts whose raw body is far larger than a practical
single provider request. A single structure-adjudication or embedding request
can therefore time out or exceed the provider context boundary. A failed
embedding must remain an absent signal, but a prior run must not make that
post appear complete and prevent retry.

## Decision

1. `post_content_persistence` sends structure and embedding work through
   bounded batches of at most 32 units and 24,000 characters per provider
   request.
2. Structure adjudication receives at most 8,000 characters from any one
   unit, with an explicit truncation marker. The original DOM unit and its
   stored text are never truncated or rewritten.
3. A failed structure or embedding batch is isolated. Successful batches are
   persisted; failed batches leave their signal absent and eligible for a
   later retry.
4. `backfill_post_content` selects posts with either no content units or at
   least one content unit without an embedding. It requires a configured
   contextual-orchestrator embedding channel before writing content artifacts.
5. This is request-size and retry policy, not model selection. Model choice,
   reasoning effort, VISION, and provider protocol negotiation remain owned by
   contextual-orchestrator under ADR 0076.

## Consequences

- Large real posts no longer block the entire resumable backfill on one
  provider request.
- A structure decision based on a truncated adjudication view remains the
  model's evidence-backed decision; unresolved or failed decisions remain
  `unresolved` rather than being replaced by a heuristic.
- Backfill coverage can be measured directly as content posts versus posts
  with persisted vectors, and reruns converge without deleting source data.

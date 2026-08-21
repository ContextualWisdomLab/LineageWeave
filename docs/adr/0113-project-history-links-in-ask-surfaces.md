# ADR 0113: Reuse canonical project history in Ask surfaces

- Status: Proposed
- Date: 2026-08-21
- Depends on: ADR 0112 and the canonical Project history read model

## Context

Post-scoped Ask and Global Ask already cite authorized source posts, but they did not
connect those citations to the project lifecycle timeline shown in the product design.
The earlier orphaned stack attempted to solve this with another project-history flow.
That would create competing project identity, authorization, cutoff, classification, and
TEPP behavior.

Persisted Ask prose introduces an additional security boundary: if a previously cited
post becomes hidden, deleted, draft, or otherwise ineligible, returning the old answer or
reusing it as conversation context can disclose facts no longer authorized.

## Decision

1. Ask responses expose structured project-history links derived only from cited post IDs.
2. Citation IDs are reauthorized with tenant ABAC, source publication eligibility, and the
   answer knowledge cutoff before titles or project identities are returned.
3. Exact source project fields outrank semantic project candidates; inferred identities
   remain labelled inferred. Links are bounded and deterministic.
4. Opening a link calls the canonical Project history endpoint with project key, answer
   cutoff, and cited focus post. The established timeline and TEPP metadata are reused.
5. A persisted post answer is withheld in full when any citation is no longer authorized.
   Its prose cannot be safely decomposed by source after access changes.
6. A Global Ask session is rejected and restarted when any citation in its persisted
   continuity context is no longer authorized. Stored summaries are not reused across
   that boundary.
7. Ask retrieval itself applies the same cutoff and source eligibility before an LLM sees
   evidence. Prompt bodies, hidden IDs, and unauthorized project counts never enter the
   project-history link response.
8. Timeline or TEPP failure does not remove the answer; the Buyer receives an actionable
   error and can still open the exact cited source post.

## Consequences

- Document reading, post Ask, Global Ask, and the dedicated Project history destination
  share one authorization-first read model and one timeline component.
- Historical answers can disappear after permission or publication changes. This is an
  intentional fail-closed property, not data loss from the evidence store.
- A session restart can lose conversational convenience, but prevents a compressed
  summary from carrying hidden prose forward.
- Event order remains a temporal association and is not presented as causal inference.

## Rejected alternatives

- Parse project identities from answer prose. This is nondeterministic and ungrounded.
- Build a second project query or timeline inside Ask. This duplicates authority.
- Return a stored answer while merely hiding its citation chips. The prose may still leak
  the hidden source.
- Keep a stale Global Ask summary and filter only new citations. The summary cannot be
  safely decomposed after authorization changes.

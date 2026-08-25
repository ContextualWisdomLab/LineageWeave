# ADR 0064: Keep lineage as uncertainty-bearing evidence

- Status: Accepted
- Date: 2026-08-19
- Amended by: [ADR 0200](0200-channel-weight-reconciliation.md) and
  [ADR 0205](0205-tepp-lineage-anchor.md)

## Context

Short business records are scattered across customers, projects, and other
coarse keys. A nearest-predecessor rule can attach unrelated topics and turns
a weak signal into an apparently certain history. LineageWeave must provide a
browsable tree without claiming TEPP-style calibrated psychometric measurement
or promoting an inferred relation to fact.

## Decision

- Treat every input record as a fallible mention and every accepted edge as a
  lineage instance supported by evidence, not as a proven business fact.
- Fuse independent temporal, secondary-key, text/embedding, and optional LLM
  channels through the RankWeave weighted convex fusion contract. Resolve a
  missing channel before loading the exact calibrated active-channel vector;
  never repair or renormalize a vector estimated for another channel set, and
  never replace a missing channel with a fabricated negative or score.
- Keep the channel-score breakdown and provenance on every candidate decision.
  Candidates below the minimum fused-score floor remain roots rather than being
  force-attached.
- Enforce the before-or-equal time boundary structurally when selecting a
  parent, then delegate tree assembly to ThreadWeave.
- Route LLM adjudication through contextual-orchestrator only. LineageWeave
  never calls a raw LLM API and never presents its output as TEPP measurement.

## Consequences

- Buyers can inspect why a relation was selected and distinguish inference from
  source evidence.
- Multi-topic histories remain branching roots instead of receiving a false
  deterministic chain.
- The graph is less complete when signals are unavailable or below threshold,
  but the product does not hide uncertainty behind invented links.

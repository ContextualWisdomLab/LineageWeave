# ADR 0064: Keep lineage as uncertainty-bearing evidence

- Status: Accepted
- Date: 2026-08-19

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
  channels through the RankWeave weighted convex fusion contract. A missing
  channel is dropped and weights are renormalized; it is never replaced with a
  fabricated negative or score. A structured `refuted` verdict remains a real
  negative score; `insufficient_evidence` drops the LLM channel for that whole
  candidate comparison so every candidate is ranked with the same weights.
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

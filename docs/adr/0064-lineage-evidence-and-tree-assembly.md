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
  fabricated negative or score.
- Keep the channel-score breakdown and provenance on every candidate decision.
  Candidates below the minimum fused-score floor remain roots rather than being
  force-attached.
- Enforce the before-or-equal time boundary structurally when selecting a
  parent, then delegate tree assembly to ThreadWeave.
- Route LLM adjudication through contextual-orchestrator only. LineageWeave
  never calls a raw LLM API and never presents its output as TEPP measurement.
- Corpus-wide reconstruction obtains its source rows before invoking the
  synchronous adjudication adapter, runs that blocking adapter outside the
  asyncio event-loop thread, and propagates the request context into that
  worker thread. A provider or response-contract failure aborts before the
  stored lineage projection is changed.
- Replace the stored lineage projection in one short PostgreSQL transaction
  after reconstruction succeeds. The delete-and-insert replacement remains
  atomic, while provider latency does not hold that write transaction open.

## Consequences

- Buyers can inspect why a relation was selected and distinguish inference from
  source evidence.
- Multi-topic histories remain branching roots instead of receiving a false
  deterministic chain.
- The graph is less complete when signals are unavailable or below threshold,
  but the product does not hide uncertainty behind invented links.
- Other API work remains responsive during a corpus-wide adjudication, and a
  failed adjudication leaves the previously stored projection intact. The API
  reports that temporary dependency failure as retryable unavailability.

## References — APA 7th

PostgreSQL Global Development Group. (2026). *Transactions* (PostgreSQL 18
documentation). https://www.postgresql.org/docs/current/tutorial-transactions.html

Python Software Foundation. (2026). *Coroutines and tasks* (Python 3.14.6
documentation). https://docs.python.org/3/library/asyncio-task.html#running-in-threads

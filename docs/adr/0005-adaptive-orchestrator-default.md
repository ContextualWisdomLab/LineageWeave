# ADR-0005: Adaptive contextual-orchestrator mode is the consumer default

- Status: Accepted
- Date: 2026-08-15

## Context

LineageWeave previously forced `mode="route"` in summarization, post evaluation,
Keyman extraction, commitment extraction, post chat, and relationship
classification. That made the consumer choose a single model before
contextual-orchestrator could evaluate task difficulty, capability fit,
verification need, and known model price.

Research on adaptive orchestration and cost-aware reliability shows that no fixed
model/workflow/budget choice dominates for all requests. Dynamic scaffolding and
query-level cost allocation are therefore responsibilities of the orchestration
plane, not of each domain client.

## Decision

Active general-purpose clients request `mode="auto"`.

- contextual-orchestrator selects the quality-sufficient route, bounded
  verification, or conducted workflow and then minimizes known cost inside the
  selected capability tier;
- LineageWeave continues to own prompts, schemas, strict parsing, domain evidence,
  and failure semantics;
- the low-volume lineage adjudication channel retains the explicit `verify`
  override because an independently checked verdict is part of that domain
  contract, not an accidental routing default;
- explicit modes remain permitted for ablation, regression comparison, and
  emergency operator policy, but they are not ordinary production defaults.

## Consequences

Trace width is no longer a stable consumer assumption for `auto` requests.
Telemetry and tests must record the requested policy and actual trace. Cost
claims require configured price evidence; an unpriced model is never treated as
free.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic framework for LLM agents: Cost-aware adaptive reliability* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228

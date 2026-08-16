# ADR-0005: Product LLM clients delegate default execution to contextual-orchestrator auto

- Status: Accepted
- Date: 2026-08-16

## Context

LineageWeave had several independent feature adapters for summarization, Keyman
extraction, relationship classification, commitments, chat, and post evaluation.
Each adapter hard-coded `route`, which duplicated policy and forced a single worker
regardless of uncertainty, risk, or task complexity. Adjudication separately uses
`verify` because it is an explicit controlled worker-plus-checker contract.

## Decision

Every production adapter that does not intentionally implement a controlled
ablation sends `mode="auto"`. Contextual-orchestrator owns model/provider selection,
reasoning effort, verification depth, failover, and the quality-first/cost-aware
execution tier. The explicit adjudication `verify` contract remains unchanged.

The application still owns prompt semantics, strict parsers, typed domain records,
tenant authorization, persistence, and fail-closed handling. Auto orchestration is
not permission to accept malformed or unsupported model output.

## Consequences

A simple extraction may still resolve to one worker when that is the
quality-sufficient least-cost plan. Evaluation and uncertain classification can use
a verifier, while complex synthesis can use a conducted workflow, without changing
LineageWeave's public interfaces. Returned trace and usage evidence remain available
for empirical calibration.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic framework for LLM agents: Cost-aware adaptive reliability* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228

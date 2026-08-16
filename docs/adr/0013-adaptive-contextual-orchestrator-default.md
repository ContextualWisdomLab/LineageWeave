# ADR-0013: Adaptive contextual-orchestrator mode is the default

- Status: Accepted
- Date: 2026-08-16

## Context

LineageWeave used fixed single-worker `route` mode for structured extraction, summarization, commitment derivation, relationship classification, and post evaluation. That made each consumer choose the execution topology and prevented `contextual-orchestrator` from allocating deeper verification when task difficulty, uncertainty, or risk justified it.

## Decision

Ordinary LineageWeave LLM consumers request `mode="auto"`. That includes structured extraction, summarization, commitment derivation, relationship classification, post evaluation, and vision OCR/captioning when the client is built by `orchestrator_vision_client`. A generic `OpenAiCompatibleVisionClient` omits `mode` so an OpenAI-compatible gateway that rejects unknown fields still works.

The orchestration plane owns provider/model selection, test-time compute, workflow depth, verification, fallback, and known-price optimization. Quality sufficiency is the first constraint; cost is minimized among execution paths that satisfy it. Unpriced models are not treated as free.

Explicit `verify` remains for the citation-bearing post-chat and lineage adjudication paths because those are deliberate checked-judgment contracts, not product defaults. Explicit route or conduct modes may be used only for documented ablation, incident response, or a bounded domain requirement.

LineageWeave continues to own strict output parsing, evidence identifiers, IRT projection, and fail-closed domain validation.

## Consequences

A structured task may still be served by one model when the adaptive policy determines that it is sufficient. Harder requests may receive a deeper workflow without changing the LineageWeave API. Consumers must retain returned orchestration and usage evidence when the gateway exposes it.

Contract tests walk the AST for a payload-level `"mode": "auto"` or `"mode": "verify"` literal (or, for post-evaluation, `"mode": mode` plus `mode: str = "auto"`; for vision, the orchestrator factory passes `mode="auto"` and `describe()` writes it onto the body). A docstring mention of `mode="auto"` or `mode="verify"`, including a quoted `{"mode": "auto"}` fragment, is not sufficient. Wire tests call `answer()` / `judge()` / `evaluate()` / `describe()` and assert the outbound body.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic framework for LLM agents: Cost-aware adaptive reliability* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228

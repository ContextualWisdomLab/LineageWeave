# ADR 0025 — Fail-closed contextual-orchestrator task envelope

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

Issue #79 requires a versioned fail-closed REST adapter until reviewed
upstream `contextual-orchestrator` main exposes the required portable
task envelope. Structured extraction already requests `auto` (ADR 0013).
Checked judgment (lineage adjudication, citation-bearing chat) still
requests `verify`. Deployed upstream `main` accepts
`auto` / `route` / `conduct`; `verify` can return `invalid_mode`
until `ContextualWisdomLab/contextual-orchestrator#149` lands.

A missing host, a missing key, or `invalid_mode` must not become an
invented completion, a confidence of 0.0, or a TEPP theta. RankWeave
status stays on ADR 0024. TEPP stays on #214. This slice does not
bind demo Keycloak to production Keyverse.

## Decision

1. Consume the orchestrator only through `OrchestratorClient`. The
   default transport raises `OrchestratorNotAvailable`.
   `build_orchestrator_client` publishes the envelope only when both
   `ORCHESTRATOR_BASE_URL` and `ORCHESTRATOR_API_KEY` are set.
2. The portable envelope is closed (`additionalProperties` stay out):
   `contract_version`, `task_kind`, `mode`, `reasoning_effort`,
   `prompt_hash`, `access_list`. Structured work uses `auto` /
   `medium`. Checked judgment uses `verify` / `high`.
3. `GET /api/orchestration` (`post_read`) returns buyer status. Home
   GET never POSTs `/v1/chat/completions`. An `invalid_mode` transport
   error is `orchestrator_invalid_mode`, never a fabricated score.
4. After login, Orchestration sits above Rankings. Unavailable copy is
   **Orchestration · contextual-orchestrator not available**. An
   accepted row names **Structured work uses auto** and
   **Checked judgment uses verify**.

## Consequences

Demo compose without orchestrator credentials fail-closes on home.
Wiring a live submit transport is additive. Adjudication still owns
pair-wise `verify` calls; this port does not invent their verdicts.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic
framework for LLM agents: Cost-aware adaptive reliability* [Preprint].
arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda,
H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S.,
Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report*
[Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228

Contextual Wisdom Lab. (2026). *Contextual orchestrator* [Software
documentation].
https://github.com/ContextualWisdomLab/contextual-orchestrator

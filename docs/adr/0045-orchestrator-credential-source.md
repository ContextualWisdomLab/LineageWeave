# ADR 0045: Contextual-orchestrator credential source

- Status: Accepted
- Date: 2026-08-18

## Context

LineageWeave calls contextual-orchestrator rather than a raw LLM provider.
The orchestrator authenticates its gateway boundary with the canonical
`LLM_GATEWAY_API_KEY`. A separate backend development default can silently
produce HTTP 401 when `~/.env` contains the real gateway credential.

## Decision

The backend's internal orchestrator credential resolves in this order:

1. Explicit `ORCHESTRATOR_API_KEY` override.
2. Internal `CONTEXTUAL_ORCHESTRATOR_TOKEN` service credential.
3. The documented development-only fallback when no internal credential is configured.

The orchestrator URL remains the internal `orchestrator` service boundary.
`CONTEXTUAL_ORCHESTRATOR_TOKEN` authenticates that internal service boundary;
`LLM_GATEWAY_API_KEY` and `LLM_GATEWAY_URL` configure the provider gateway and
are never used as the internal service credential. GitHub/external runs inject
the canonical gateway variables; local Compose reads `~/.env` and accepts the
compatibility aliases. No raw provider credential or token is printed or
committed.

The pinned orchestrator's product Compose default is 4096 output tokens for
external and local gateways. This is required because Buyer summary and Ask
contracts return evidence arrays, and a 256-token local-MLX response can be
cut off before its JSON closes. `LLM_GATEWAY_MAX_OUTPUT_TOKENS` may override
the default within 64-4096; the call still crosses contextual-orchestrator and
is never sent directly from LineageWeave. A deployment that intentionally
chooses a lower budget must accept an unavailable structured result rather
than treating truncated prose as evidence.

The explicitly permitted local MLX Gemma route also receives
`chat_template_kwargs.enable_thinking=false` at the orchestrator provider
adapter. Without that compatibility field the provider can return only a
`message.reasoning` field, while the OpenAI-compatible contract requires the
answer in `message.content`; external gateway requests do not receive this
local-only field, even when the Compose local-MLX compatibility flag is set.

# ADR 0072: Gateway chat model auto-discovery

- Status: Superseded by [ADR 0076](0076-paper-grounded-model-policy.md)
- Date: 2026-08-19

> Historical record only. The first-model selection below is no longer a
> normative decision.

## Context

The LineageWeave contextual-orchestrator container must use the gateway
credentials from `~/.env`, but `LLM_GATEWAY_MODEL` must not be required. A
blank model in an OpenAI-compatible `ModelAgent` is not a valid provider
request, even when the gateway itself exposes a model catalog.

## Decision

The container bootstrap queries the configured gateway's `/v1/models` endpoint
once and selects the first model that is not marked as embedding, moderation,
speech, or image-only. That model is injected into agents whose model is blank.
An explicit model already present in the agent file is preserved. Discovery
failure or an empty chat-capable catalog stops startup; it never sends a blank
model request or silently falls back to a synthetic model.

This is a native bootstrap change, not a monkey patch. The provider key is used
only for this bootstrap request and the existing process-local credential
registration; it is not written to logs or persisted in the agent file.

## Consequences

The service can start without `LLM_GATEWAY_MODEL`, while the selected model is
visible in the orchestrator's agent state and is used consistently for chat,
Vision, and provider readiness probes. Provider model ordering remains the
gateway's policy; if capability metadata becomes available later, the filter
can be tightened without changing the public configuration contract.

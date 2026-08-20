# ADR 0088: Delegate Provider Protocol Negotiation to contextual-orchestrator

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave sends Chat Completions-shaped requests through
contextual-orchestrator. Some provider agents expose only the Responses API,
and multimodal requests can be rejected by a provider's Chat endpoint even
when the same model supports the equivalent Responses input. A client-side
fallback or monkey patch would split provider capability policy across this
repository.

## Decision

LineageWeave remains Chat-shaped at its boundary and sends `mode=auto` and
`reasoning_effort=auto` without selecting a provider model. The pinned
contextual-orchestrator PR #761 implementation negotiates both directions:

- Chat Completions to Responses when an auto-protocol provider rejects the Chat
  endpoint or feature shape with a capability/unsupported-endpoint status.
- Responses to Chat Completions for an auto-protocol provider that rejects the
  Responses endpoint.

The translation maps `system` to `developer`, `image_url` to `input_image`,
and `json_schema`/`json_object` through the provider protocol adapter. No
LineageWeave monkey patch or direct provider call is allowed.

## Consequences

- VISION and structured requests stay behind one contextual-orchestrator
  boundary while supporting Responses-only providers.
- The upstream PR commit is pinned explicitly until protected merge completes;
  the runtime must not silently use an older implementation.
- Provider capability errors remain distinguishable from ordinary application
  errors and can trigger protocol negotiation rather than fabricated output.

# ADR 0083: Pin the runtime to the reviewed contextual-orchestrator commit

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave delegates every LLM and VISION request to contextual-orchestrator.
The orchestrator's `auto` reasoning mode is an internal routing decision and
must not be forwarded as an upstream provider `reasoning_effort` value. The
runtime also must discover provider models from the configured gateway rather
than requiring `LLM_GATEWAY_MODEL`, and structured requests must remain
multi-agent.

## Decision

`docker/contextual-orchestrator/Dockerfile` pins the downloaded archive to
commit `2a1810f46bd0f2a648d2236266e2e5d54a6738bb`. The pin remains explicit
and immutable until the reviewed upstream change is superseded; it is not a
moving `main` reference and it is not a LineageWeave monkey patch.

The runtime contract is:

- LineageWeave may send `reasoning_effort="auto"` to the orchestrator.
- contextual-orchestrator resolves `auto` using its capability/routing policy.
- Only an explicit supported effort is sent to an upstream provider.
- Structured output uses prompt-constrained final synthesis inside
  contextual-orchestrator and validates the requested `json_object` or
  `json_schema` contract locally; it is not a provider passthrough.
- This negotiation preserves multi-agent worker and synthesis calls and never
  collapses a structured request to a single-agent passthrough.
- Multimodal synthesis excludes embedded image/base64 payloads from its textual
  reconciliation prompt; independent VISION worker evidence is retained instead.
- A provider 4xx is reported as a failed orchestration attempt, never as a
  successful empty semantic result.
- An empty seed model is expanded from configured provider discovery endpoints;
  provider-declared embedding rows enter the embedding pool but never a chat role.
- Runtime discovery activates provider-declared chat and embedding capabilities.
  LineageWeave does not configure or infer an embedding provider/model pair.
- A batch embedding request may omit `model`; contextual-orchestrator selects
  an embedding-capable model and returns its identity for subsequent batches.
- A blank embedding input fails before provider selection; it is never sent as
  a successful empty semantic signal.
- An explicit remote agent tagged `embedding` uses its provider-backed
  embedding transport rather than a local placeholder implementation.
- `json_object`, `json_schema`, and Responses JSON formats run conduct plus
  synthesis. Tool requests never silently fall back to one agent.

## Consequences

- Local Compose runtime and the reviewed upstream PR use the same orchestrator
  implementation.
- Rebuilding the image is required after the upstream pin changes.
- Protected-branch review and merge remain external gates; this pin does not
  bypass upstream review.

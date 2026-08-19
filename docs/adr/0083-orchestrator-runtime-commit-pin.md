# ADR 0083: Pin the runtime to the reviewed contextual-orchestrator commit

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave delegates every LLM and VISION request to contextual-orchestrator.
The orchestrator's `auto` reasoning mode is an internal routing decision and
must not be forwarded as an upstream provider `reasoning_effort` value. The
LineageWeave orchestrator image was pinned to an older archive commit that did
forward that value, causing real provider HTTP 400 responses during semantic
backfill even though the local contextual-orchestrator PR had the correction.

## Decision

`docker/contextual-orchestrator/Dockerfile` pins the downloaded archive to
commit `af228e5`, the pushed head of contextual-orchestrator PR #761. The pin
remains explicit and immutable until the protected PR merges; it is not a
moving `main` reference and it is not a LineageWeave monkey patch.

The runtime contract is:

- LineageWeave may send `reasoning_effort="auto"` to the orchestrator.
- contextual-orchestrator resolves `auto` using its capability/routing policy.
- Only an explicit supported effort is sent to an upstream provider.
- Structured output negotiates `json_schema`, then `json_object`, then
  prompt-only synthesis inside contextual-orchestrator when a provider returns
  a capability `400` or `422`; the requested JSON contract is validated locally.
- This negotiation preserves multi-agent worker and synthesis calls and never
  collapses a structured request to a single-agent passthrough.
- Multimodal synthesis excludes embedded image/base64 payloads from its textual
  reconciliation prompt; independent VISION worker evidence is retained instead.
- A provider 4xx is reported as a failed orchestration attempt, never as a
  successful empty semantic result.

## Consequences

- Local Compose runtime and the reviewed upstream PR use the same orchestrator
  implementation.
- Rebuilding the image is required after the upstream pin changes.
- Protected-branch review and merge remain external gates; this pin does not
  bypass PR #761.

# ADR 0070: Integrate contextual-orchestrator through upstream contracts only

- Status: Accepted
- Date: 2026-08-19
- Depends on: ADR 0030, ADR 0067
- Related: `ContextualWisdomLab/contextual-orchestrator`

## Context

LineageWeave delegates text, embedding, and VISION work to
`contextual-orchestrator`. Some providers expose Chat Completions, while
others expose only the Responses API. Responses uses `developer` for the
instruction role; Chat Completions uses `system`. Model selection must also
remain inside the orchestrator rather than being hard-coded in LineageWeave.

Changing imported orchestrator classes or methods at runtime would make the
effective API differ from the upstream contract, hide incompatibilities until
container startup, and make upgrades unsafe.

## Decision

LineageWeave MUST NOT monkey-patch `contextual-orchestrator` or copy its
implementation into this repository to add provider behavior. The following
are prohibited:

- Assigning or wrapping upstream classes/functions at runtime from
  `start.py` or another application module.
- Maintaining a private fork or vendored copy in the LineageWeave image as a
  substitute for an upstream change.
- Selecting `LLM_GATEWAY_MODEL` or `VISION_MODEL` in LineageWeave to bypass a
  missing orchestrator capability.

Provider protocol capability discovery, Chat Completions/Responses API
translation, `system`/`developer` role conversion, response extraction, and
automatic model selection belong in the
`ContextualWisdomLab/contextual-orchestrator` repository. The upstream change
must include its own unit and integration tests and be merged through its
normal review process. LineageWeave then pins the reviewed immutable upstream
commit in its Docker build and uses only the published orchestrator contract.

An operator may set `ORCHESTRATOR_ROUTING_ENDPOINT` at the backend, worker,
and MCP process boundary. LineageWeave adds that opaque selector as
`routing.endpoint` only to contextual-orchestrator requests whose parsed path
is exactly `/v1/chat/completions` or `/v1/responses`. Existing routing fields
are preserved; a non-object routing value or a conflicting endpoint fails
before transport. The selector is not applied to embeddings, batch routes,
model discovery, or other HTTP services, and an unset selector retains the
existing automatic routing behavior.

Until that commit is available, the affected capability is unavailable rather
than silently routed through a local patch or a guessed model. A LineageWeave
change is complete only when the pinned upstream commit starts successfully
and its runtime evidence proves the selected provider protocol and role
translation.

## Alternatives considered

1. Runtime monkey patch in the LineageWeave container. Rejected because it
   couples behavior to private upstream internals and breaks upgrade and
   provenance guarantees.
2. A LineageWeave-only fork or copied provider adapter. Rejected because it
   creates two incompatible orchestrator implementations and duplicates
   provider governance.
3. Upstream implementation followed by immutable commit pinning. Accepted
   because the capability is tested and governed at the system boundary that
   owns provider routing.

## Consequences

- The orchestrator repository and this repository require a coordinated
  change, and delivery can wait on upstream review.
- LineageWeave has a smaller integration surface and no runtime mutation of
  third-party code.
- Provider-specific Responses handling and role semantics are reusable by all
  orchestrator clients, including VISION and future model providers.
- A missing or unmerged upstream capability is visible as a blocked channel,
  not a fabricated success or an untracked fallback.

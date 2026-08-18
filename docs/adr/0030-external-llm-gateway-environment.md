# ADR-0030: External LLM gateway environment boundary

- **Status:** Accepted
- **Date:** 2026-08-18

## Context

LineageWeave must send every LLM request through
[contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator).
The provider gateway is an operational secret and must not be copied into the
repository, an image, a fixture, a test, or a GitHub workflow.

Compose has two distinct authenticated hops:

1. `LineageWeave -> contextual-orchestrator`, configured by
   `ORCHESTRATOR_BASE_URL` and `ORCHESTRATOR_API_KEY`.
2. `contextual-orchestrator -> LLM gateway`, configured by
   `LLM_GATEWAY_URL` and `LLM_GATEWAY_API_KEY`.

These credentials are not interchangeable. The first is the local service
boundary; the second is the provider credential.

## Decision

For local and other non-GitHub runtimes, the provider variables are read from
`~/.env` using these exact names:

```text
LLM_GATEWAY_URL
LLM_GATEWAY_API_KEY
```

`make up`, `make down`, `make logs`, and `make ps` pass that file to Compose
with `--env-file`, so its variable interpolation and the orchestrator's
`env_file` use the same source. The API key remains process/container
environment data and is never logged, rendered into frontend assets, or
checked in.

GitHub Actions must not depend on a developer's `~/.env`. If a workflow needs
the provider, it must inject the same two names from GitHub-managed secrets at
runtime, with masking enabled; the repository contains no provider secret.

The contextual-orchestrator service remains the only LLM boundary. LineageWeave
does not call the provider gateway directly and does not create a fallback
local score, summary, extraction, or answer when the gateway is unavailable.

## Consequences

- Provider changes are deployment configuration, not source changes.
- A missing or invalid gateway credential fails at the orchestrator boundary;
  it must not be replaced by a fabricated channel result.
- `CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS` must explicitly allow the
  hostname selected by `LLM_GATEWAY_URL`; wildcard allowlists are forbidden.
- `LLM_GATEWAY_MODEL` must be authorized by that gateway. A local-MLX model
  name cannot be assumed to be available on an external provider.
- `LLM_GATEWAY_EMBEDDING_MODEL` is the explicit allowlisted semantic embedding
  model. If it is absent, contextual-orchestrator rejects embedding work
  instead of returning its standalone eight-dimensional heuristic vector.
- `LLM_API_KEY` and `LLM_API_GATEWAY` are not supported aliases in this repo;
  using the canonical names avoids silently selecting the wrong hop.

Vision follows the same boundary. LineageWeave sends image content blocks only
to contextual-orchestrator's internal OpenAI-compatible endpoint; it never
sends image bytes directly to `LLM_GATEWAY_URL`. The contextual-orchestrator
container validates the supported `text` and `image_url` blocks and forwards
the multimodal request to the configured provider. Image data is excluded from
the text used for workflow routing and reasoning classification.

Before the image content block is built, the backend decodes supported raster
formats, applies EXIF orientation, composites transparent pixels onto white,
and encodes the payload as PNG. Invalid or undecodable image bytes fail closed;
they are never forwarded as an unvalidated provider request.

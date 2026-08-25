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
   `LLM_GATEWAY_API_URL` and `LLM_GATEWAY_API_KEY`.

These credentials are not interchangeable. The first is the local service
boundary; the second is the provider credential.

The backend must not load `~/.env` wholesale. Compose injects the provider
credential and URL only into contextual-orchestrator; the backend receives
only its internal orchestrator credential. This prevents an unrelated
application process from holding the provider secret while preserving the
single LLM/Vision/embedding boundary.

## Decision

For GitHub Actions and any deployment that injects canonical secrets, the
provider variables use these exact names:

```text
LLM_GATEWAY_API_KEY
LLM_GATEWAY_API_URL
```

For the operator's local `~/.env`, Compose also accepts the existing names
`LLM_GATEWAY_URL`, `LLM_API_GATEWAY`, and `LLM_API_KEY` and maps them to the
canonical provider variables. Canonical values win when both names are present.
`make up`,
`make down`, `make logs`, and `make ps` pass that file to Compose with
`--env-file`, so its interpolation and the orchestrator's `env_file` use the
same source. The API key remains process/container environment data and is
never logged, rendered into frontend assets, or checked in.

GitHub Actions must not depend on a developer's `~/.env`. If a workflow needs
the provider, it must inject the same two names from GitHub-managed secrets at
runtime, with masking enabled; the repository contains no provider secret.

The contextual-orchestrator service remains the only LLM boundary. LineageWeave
does not call the provider gateway directly and does not create a fallback
local score, summary, extraction, or answer when the gateway is unavailable.
Provider response envelopes and exceptions are also a trust boundary: clients
extract only the expected content and expose stable, next-action-safe error
messages. Raw provider response bodies, exception text, prompts, and secrets
must never be returned through a buyer-facing API or persisted failure detail.

## Consequences

- Provider changes are deployment configuration, not source changes.
- A missing or invalid gateway credential fails at the orchestrator boundary;
  it must not be replaced by a fabricated channel result.
- A provider failure is logged with internal correlation context where
  operational logging permits, but the buyer receives a stable unavailable
  message that tells them to retry or restore the provider configuration.
- `CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS` must explicitly allow the
  hostname selected by `LLM_GATEWAY_API_URL`; wildcard allowlists are forbidden.
- Local Compose development permits only the explicitly enumerated
  `host.docker.internal:8080` text gateway and `host.docker.internal:18082`
  Vision gateway when `LINEAGEWEAVE_ALLOW_LOCAL_LLM_HTTP=1`; arbitrary local
  HTTP ports remain rejected.
- `LLM_GATEWAY_MODEL` and `VISION_MODEL` are not selected by LineageWeave.
  When they are blank, contextual-orchestrator resolves the registered agent
  model, so a local or provider-specific model name cannot leak into this
  application or be assumed available on an external gateway.
- LineageWeave does not configure an embedding model. Its first batch request
  omits `model`; contextual-orchestrator selects a provider-neutral embedding
  model and returns that identity on submission and polling responses.
  LineageWeave binds that identity for later batches and persists it with every
  vector. A missing or changed identity, or an incomplete vector batch, fails
  closed and cannot make post content complete.
- `LLM_API_KEY`, `LLM_API_GATEWAY`, and `LLM_GATEWAY_URL` are compatibility
  aliases only; `LLM_GATEWAY_API_KEY` and `LLM_GATEWAY_API_URL` are the
  canonical names for
  GitHub and deployment automation.

Vision follows the same boundary. LineageWeave sends image content blocks only
to contextual-orchestrator's internal OpenAI-compatible endpoint; it never
sends image bytes directly to `LLM_GATEWAY_API_URL`. The contextual-orchestrator
container validates the supported `text` and `image_url` blocks and forwards
the multimodal request to the configured provider. Image data is excluded from
the text used for workflow routing and reasoning classification.

The upstream HTTP server keeps its ordinary JSON body default at 64 KiB. The
LineageWeave Compose bootstrap passes the explicit bounded
`CONTEXTUAL_ORCHESTRATOR_MAX_BODY_BYTES` value, defaulting to 8 MiB, because
normalized image blocks are base64 data URIs. The limit is bounded at 64 MiB;
unbounded request bodies and per-image provider bypasses are forbidden.

The selected provider/model must actually support multimodal `image_url`
content. A text-only gateway response such as `Only 'text' content type is
supported` is a provider capability failure, not a successful Vision result;
the channel remains unavailable and no OCR/caption is fabricated.

Before the image content block is built, the backend decodes supported raster
formats, applies EXIF orientation, composites transparent pixels onto white,
and encodes the payload as PNG. Invalid or undecodable image bytes fail closed;
they are never forwarded as an unvalidated provider request.

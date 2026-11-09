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
3. No credential: the client stays unconfigured, so every orchestrator
   channel is the unavailable Null client (dropped, not faked).

The orchestrator URL remains the internal `orchestrator` service boundary.
`CONTEXTUAL_ORCHESTRATOR_TOKEN` authenticates that internal service boundary;
`LLM_GATEWAY_API_KEY` and `LLM_GATEWAY_API_URL` configure the provider gateway
and are never used as the internal service credential. GitHub/external runs and
local Compose use these canonical gateway variables from `~/.env` or the
deployment environment; `LLM_GATEWAY_URL`, `LLM_API_GATEWAY`, and `LLM_API_KEY`
are compatibility aliases only. No raw provider credential or token is printed
or committed.

The pinned orchestrator's product Compose default is 4096 output tokens for
the configured gateway. This is required because Buyer summary and Ask
contracts return evidence arrays. `LLM_GATEWAY_MAX_OUTPUT_TOKENS` may override
the default within 64-4096; the call still crosses contextual-orchestrator and
is never sent directly from LineageWeave. A deployment that intentionally
chooses a lower budget must accept an unavailable structured result rather
than treating truncated prose as evidence.

The gateway endpoint is opaque to LineageWeave. No vendor-specific URL scheme,
port allowlist, local-server default, chat-template field, or model-specific
bootstrap exception is part of this contract. Provider capability translation
belongs to contextual-orchestrator.

## Amendment (2026-11-09): no public client fallback

The orchestrator bootstrap (`docker/contextual-orchestrator/start.py`)
rejects a missing token and the public `lineageweave-orchestrator-dev-only`
value. A client that still defaulted to that public value could never
authenticate: under a plain `docker compose up` (no `--env-file`) the
orchestrator read the private token from its `env_file` while backend and
mcp interpolated the public default, so every LLM channel failed at the
internal authentication boundary instead of failing visibly. Backend and
mcp therefore default to an empty credential. With no client token the
channels are unavailable instead of failing authentication. The orchestrator
reads `CONTEXTUAL_ORCHESTRATOR_TOKEN` from `${HOME}/.env`, but backend and mcp
receive it only through Compose interpolation: a plain `docker compose up`
leaves their value empty, so their channels stay unavailable. For both
clients to receive the token, pass `--env-file "$HOME/.env"` (as `make up`
does) or export the token in the shell. This removes the third fallback step
above and does not change the override order or any provider credential.

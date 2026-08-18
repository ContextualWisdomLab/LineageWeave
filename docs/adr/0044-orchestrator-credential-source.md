# ADR 0044: Contextual-orchestrator credential source

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

# ADR 0300: Contextual-orchestrator owns the provider runtime boundary

- Status: Accepted
- Date: 2026-09-01
- Supersedes: the LineageWeave-owned provider deployment and credential portions of ADR 0030, ADR 0045, ADR 0072, ADR 0076, and ADR 0083
- Preserves: ADR 0070's upstream-contract-only principle
- Related: `ContextualWisdomLab/contextual-orchestrator`, `ContextualWisdomLab/fast-mlsirm`, `ContextualWisdomLab/TEPP`

## Context

LineageWeave owns measurement policy, source-evidence binding, instrument and rubric administration, pilot lifecycle, interpretation, and audit. It consumes LLM judgments as fallible observations. It does not own provider selection or an LLM serving runtime.

The repository nevertheless accumulated an embedded contextual-orchestrator container bootstrap, a LineageWeave-owned model-agent file, provider endpoint and credential variables, and operator-script fallbacks that could treat a provider gateway as though it were the contextual-orchestrator service. Those paths create two sources of truth for provider discovery and credentials and allow a consumer to bypass the orchestration layer accidentally.

The canonical owner is `ContextualWisdomLab/contextual-orchestrator`. Its published versioned contract owns provider/model discovery, routing and fallback, structured-output compatibility, test-time-compute allocation, role-specific reasoning effort, multi-agent orchestration, usage/cost provenance, provider credentials, and provider protocol translation.

## Decision

LineageWeave is only a contextual-orchestrator consumer.

Production and operator code in this repository may configure the LLM boundary only with:

- `ORCHESTRATOR_BASE_URL`: the published contextual-orchestrator service endpoint.
- `ORCHESTRATOR_API_KEY`: the consumer credential accepted by that service.

LineageWeave MUST NOT accept provider endpoints, provider API keys, provider-specific model-agent configuration, or contextual-orchestrator owner-process credentials as substitutes for those consumer settings. In particular, provider-gateway aliases and provider API-key names are not LineageWeave runtime configuration.

The default Compose stack MUST NOT build or start contextual-orchestrator. Operators deploy or select contextual-orchestrator through its canonical owner path and then point LineageWeave at the published service contract. With no configured orchestrator endpoint or consumer credential, LLM, VISION, embedding, judge, explanation, extraction, and other model-backed channels remain unavailable or fail closed according to their existing Null-client contracts. There is no direct-provider fallback.

All LineageWeave LLM capabilities follow this dependency direction:

`LineageWeave measurement policy/evidence -> contextual-orchestrator judge orchestration -> versioned judge observations/provenance -> fast-mlsirm psychometric computation -> optional TEPP temporal/multilevel analysis -> LineageWeave interpretation/admin/audit`.

Provider DTOs and orchestration internals are outside the LineageWeave domain model. Wire compatibility is isolated behind LineageWeave's contextual-orchestrator client adapters. Reusable psychometric numerical kernels remain owned by fast-mlsirm; temporal/event/multilevel measurement semantics remain owned by TEPP.

## Architectural fitness

Repository tests enforce that:

1. `docker/contextual-orchestrator` is absent.
2. production/runtime Python does not accept provider credential or provider-gateway configuration names.
3. `.env.example` exposes only the contextual-orchestrator consumer endpoint and consumer credential for LLM integration.
4. `docker-compose.yml` does not own an orchestrator service or provider configuration and passes only `ORCHESTRATOR_BASE_URL` / `ORCHESTRATOR_API_KEY` to LineageWeave processes.

These tests are ownership checks, not a ban on historical or normative documentation naming upstream provider variables when explaining why they are outside this bounded context.

## Consequences

- Provider configuration and credentials have one canonical owner.
- Updating contextual-orchestrator no longer requires a LineageWeave-local provider bootstrap or model-agent copy.
- Local development that needs LLM behavior must run or reach contextual-orchestrator separately. The deterministic LineageWeave stack remains usable with model-backed channels unavailable.
- A contextual-orchestrator outage or missing contract configuration is visible as an unavailable model-backed capability, never as a provider fallback.
- Existing documentation that describes LineageWeave as loading provider credentials into a local orchestrator container is stale under this ADR and must migrate to the consumer-only contract.

## Migration and rollback

Migration removes the embedded orchestrator Docker bootstrap and provider-owned environment variables, narrows operator scripts to the published consumer contract, and adds architectural fitness tests. Consumer behavior otherwise remains unchanged: requests continue to target contextual-orchestrator's versioned HTTP contract.

Rollback of a contextual-orchestrator deployment is performed in the contextual-orchestrator owner environment by selecting a previously reviewed owner release. Reintroducing provider credentials, provider endpoints, copied model-agent configuration, or an embedded orchestration runtime into LineageWeave is not an acceptable rollback because it recreates the ownership defect.

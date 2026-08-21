# ADR 0124: Orchestrator-owned embedding model discovery and provenance

- Status: Accepted
- Date: 2026-08-20
- Scope: LineageWeave embedding ingestion and post-content backfill
- Figma: N/A

## Context

LineageWeave must send embedding work through contextual-orchestrator. The
orchestrator can select an embedding-capable agent when the request omits a
model, but LineageWeave still read `LLM_GATEWAY_EMBEDDING_MODEL` and treated a
local model string as a prerequisite. That made the consumer contradict the
paper-grounded model boundary in ADR 0076 and the shared agent contract.

## Decision

1. LineageWeave does not read or expose a provider embedding model selector.
2. The embedding request omits `model` when no explicit compatibility value is
   supplied; contextual-orchestrator resolves the capability and returns the
   served model code.
3. Every persisted unit or visual-region embedding stores that returned model
   code in the normalized embedding table. If the boundary returns no model
   code, the vector is not persisted as provenance-bearing evidence and the
   ingestion job remains incomplete for retry.
4. Completeness checks in automatic mode require an embedding for every
   embeddable unit and described image region, regardless of model code. An
   explicit legacy model code, when supplied by a lower-level caller, retains
   exact-model completeness matching but is not a runtime configuration path.
5. The upstream contextual-orchestrator capability-selection contract is a
   dependency of this consumer change. No monkey patch, provider SDK, local
   model ranking, or sentinel model name is permitted.

## Consequences

- Runtime configuration contains only the internal orchestrator boundary; the
  provider credentials remain in `~/.env` at the orchestrator service boundary.
- Existing rows retain their actual `embedding_model_code`; no backfill uses a
  guessed or synthetic model code.
- A temporarily incomplete orchestrator response fails closed for evidence,
  while the source body remains available for retry.

## References

ContextualWisdomLab. (2026). *contextual-orchestrator capability selection
contract* (PR #789). https://github.com/ContextualWisdomLab/contextual-orchestrator/pull/789

ContextualWisdomLab. (2026). *ADR 0076: Paper-grounded model policy*.
`docs/adr/0076-paper-grounded-model-policy.md`.

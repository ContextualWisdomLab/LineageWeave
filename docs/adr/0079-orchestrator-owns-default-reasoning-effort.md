# ADR 0079: contextual-orchestrator owns default reasoning effort

- Status: Accepted
- Date: 2026-08-20
- Supersedes: The client-local default effort choices in the affected LLM channels

## Context

LineageWeave sends all LLM and VISION work through contextual-orchestrator.
Several client adapters still defaulted to `medium` or `high`, which silently
overrode the orchestrator's paper-grounded capability and workload allocation
policy. That makes the boundary claim untrue and couples a product channel to
an effort level it cannot evaluate itself.

## Decision

- Every LineageWeave contextual-orchestrator adapter defaults
  `reasoning_effort` to `auto`.
- Post evaluation also sends `reasoning_effort: auto`.
- Callers may provide an explicit supported effort for a deliberate workflow
  requirement; the adapter must forward it unchanged.
- `mode` remains `auto` except where a published structured-summary contract
  explicitly requires its route retry behavior.

## Consequences

- contextual-orchestrator decides whether and how to allocate reasoning effort.
- LineageWeave no longer silently selects `medium` or `high` for a channel.
- Explicit caller requests remain available and are covered separately from
  the default contract.

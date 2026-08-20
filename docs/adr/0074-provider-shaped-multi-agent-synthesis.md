# ADR 0074: Provider-shaped requests remain multi-agent workflows

- Status: Accepted
- Date: 2026-08-19

## Context

Requests containing `response_format`, `tools`, or using `/v1/responses` retain
provider-specific wire contracts. Treating those requests as a single-agent
passthrough avoids merging work, but it also bypasses the orchestrator's
reasoning, verification, cost, and provenance boundary.

This is also the smallest workflow consistent with the primary multi-agent
debate literature: independent model instances produce candidate reasoning,
multiple rounds may challenge those candidates, and a final judge synthesizes
the result. The debate papers do not establish a universal provider model
ranking; they support preserving independent evidence and an explicit
adjudication step.

## Decision

Contextual-orchestrator must execute these requests as workflows:

1. Select enabled worker agents and collect at least two independent provider
   responses. If only one provider is configured, invoke it for separate worker
   attempts rather than silently collapsing the workflow to one call.
2. Send the original provider contract and candidate evidence to a final
   synthesis agent.
3. Preserve the requested Chat Completions or Responses response shape,
   including structured output and tool-call fields.
4. Keep `mode` and `reasoning_effort=auto` as orchestrator-only controls; they
   must not leak to providers. Explicit reasoning effort is forwarded only when
   the selected provider declares support.
5. If a provider ignores a JSON response format, normalize a valid JSON value
   from the final synthesized text without replacing the workflow with a
   candidate response.

LineageWeave continues to call contextual-orchestrator only; it must not call a
raw LLM endpoint for this behavior.

## Research basis

- [Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325)
- [Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate](https://arxiv.org/abs/2305.19118)

## Consequences

- Structured, tool, and Responses requests receive the same multi-agent
  governance as ordinary requests.
- Latency and token cost increase because candidate and synthesis calls are
  intentional. `high` and `xhigh` use an additional candidate attempt.
- The provider model remains gateway-selected; LineageWeave does not set
  `LLM_GATEWAY_MODEL`.
- The integration pins a reviewed contextual-orchestrator commit in the Docker
  image and must retain focused contract tests plus runtime evidence.

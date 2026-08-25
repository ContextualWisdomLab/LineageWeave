# ADR 0076: Paper-grounded model and orchestration policy

- Status: Accepted
- Date: 2026-08-19
- Supersedes: [0072](0072-gateway-model-auto-discovery.md)
- Related: [0070](0070-contextual-orchestrator-upstream-integration.md), [0074](0074-provider-shaped-multi-agent-synthesis.md)

## Context

LineageWeave must not choose a gateway model by provider catalog order, model
name, parameter-count guess, or an undocumented local benchmark. Those rules
would make model quality, reasoning effort, agent count, synthesis, and VISION
behavior arbitrary and would place orchestrator policy in the wrong repository.

The contextual-orchestrator design cites the Fugu technical report, TRINITY,
and Conductor for model-pool, routing, workflow, role, and quality/latency
trade-off principles. Those papers do not justify ranking a particular
provider's model names as universally better.

The protocol portion is governed separately by the provider contract. The
current OpenAI Responses reference documents `reasoning.effort` values
including `none`, `minimal`, `low`, `medium`, `high`, and `xhigh`, and recommends
`json_schema` over the older `json_object` mode where Structured Outputs are
supported. These are wire-compatibility facts, not evidence that one model is
better than another.

## Decision

1. Every model-related architectural decision MUST cite a paper in the
   contextual-orchestrator literature register and state the exact principle
   being implemented. The source list is maintained in
   `contextual-orchestrator/docs/architecture.md` and includes:
   - [Fugu Technical Report](https://github.com/SakanaAI/fugu/blob/main/Fugu_technical_report.pdf)
   - [TRINITY: An Evolved LLM Coordinator](https://arxiv.org/abs/2512.04695)
   - [Learning to Orchestrate Agents in Natural Language with the Conductor](https://arxiv.org/abs/2512.04388)
2. Provider catalog order, model-name parsing, parameter-size guesses,
   undocumented benchmark results, and intuition MUST NOT be used as evidence
   for model quality, routing, reasoning effort, agent count, synthesis, or
   VISION selection.
3. Provider metadata may be used only for hard capability validation, such as
   excluding an embedding-only endpoint from chat. It is not a quality score.
4. Model discovery, agent-pool construction, routing, reasoning-effort
   allocation, provider protocol translation, structured synthesis, and VISION
   capability handling belong to contextual-orchestrator. LineageWeave passes
   the request through its published contract and does not select a model.
5. `LLM_GATEWAY_MODEL`, `VISION_MODEL`, and other provider-specific chat or
   vision model selectors remain unset. Runtime credentials come from `~/.env`
   through Compose `env_file`; the file and its values are never copied into a
   repository or image. The bootstrap removes and registers each available
   canonical provider credential (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
   `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_API_KEY_SUB`, and `BYTEZ_API_KEY`) in the
   orchestrator credential store; it does not alias one provider credential as
   another or choose a provider locally. If the paper-grounded policy or
   required capability is unavailable, the system reports an unavailable
   channel rather than making a guessed selection.
6. Any change to this policy requires an ADR update before implementation and
   focused tests plus runtime evidence at the orchestrator boundary.
7. The gateway endpoint is opaque and OpenAI-compatible at this boundary.
   LineageWeave MUST NOT encode an MLX/local-server URL scheme, port list,
   default endpoint, chat-template field, or vendor-specific bootstrap
   exception. Provider-specific protocol and capability translation belongs
   to contextual-orchestrator.

   The official MLX documentation describes MLX as an Apple-Silicon array
   framework with Python, C++, and Swift APIs, not as this product's provider
   gateway contract. A local MLX or `mlx-vlm` runtime may therefore appear in
   private diagnostic evidence, but it cannot be a LineageWeave configuration,
   routing, or capability contract.

## Consequences

- ADR 0072's first-catalog-model behavior is historical and non-normative.
- LineageWeave cannot repair an upstream model-policy gap with a bootstrap
  heuristic or monkey patch.
- The orchestrator repository must carry the model-policy implementation and
  its evidence; this repository pins only a reviewed upstream commit.
- A provider with insufficient capability may leave structured or VISION work
  unavailable until the upstream policy supports it.

## References

- Sakana AI. (2026). *Fugu technical report*.
- [TRINITY: An Evolved LLM Coordinator](https://arxiv.org/abs/2512.04695).
- [Learning to Orchestrate Agents in Natural Language with the Conductor](https://arxiv.org/abs/2512.04388).
- [MLX official repository](https://github.com/ml-explore/mlx).
- [MLX official documentation](https://ml-explore.github.io/mlx/).
- [OpenAI Responses API reference: reasoning and structured outputs](https://platform.openai.com/docs/api-reference/responses).
- [OpenAI Responses API quickstart: multimodal input and tools](https://platform.openai.com/docs/quickstart).
- [Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325).
- [Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate](https://arxiv.org/abs/2305.19118).

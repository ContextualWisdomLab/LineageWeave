# ADR 0083: Pin the runtime to the reviewed contextual-orchestrator commit

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave delegates every LLM and VISION request to contextual-orchestrator.
The orchestrator's `auto` reasoning mode is an internal routing decision and
must not be forwarded as an upstream provider `reasoning_effort` value. The
runtime also must discover provider models from the configured gateway rather
than requiring `LLM_GATEWAY_MODEL`, and structured requests must remain
multi-agent.

## Decision

`docker/contextual-orchestrator/Dockerfile` pins the downloaded archive to
commit `60c567c7d47aea3536ee7a7cceedbb4cd09f1c1c` from stacked upstream PR
#907. The candidate pin supplies the exact `Retry-After` admission deferral and
rate-budget-derived readiness polling cadence consumed by this stack. PR #907
remains open over PR #857, so neither the candidate pin nor local runtime
evidence is protected upstream release evidence. The pin remains explicit and
immutable until the reviewed upstream change is superseded; it is not a moving
`main` reference and it is not a LineageWeave monkey patch.
The Docker builder verifies that archive against its committed SHA-256 before
extracting it. Runtime Python packages and every transitive dependency are
installed only from `docker/contextual-orchestrator/requirements.lock` with
pip's `--require-hashes`; `requirements.in` records the three direct roots and
the lock-generation command is embedded in the generated artifact.

The runtime contract is:

- LineageWeave may send `reasoning_effort="auto"` to the orchestrator.
- contextual-orchestrator resolves `auto` using its capability/routing policy.
- Only an explicit supported effort is sent to an upstream provider.
- Structured output uses prompt-constrained final synthesis inside
  contextual-orchestrator and validates the requested `json_object` or
  `json_schema` contract locally; it is not a provider passthrough.
- This negotiation preserves multi-agent worker and synthesis calls and never
  collapses a structured request to a single-agent passthrough.
- Multimodal synthesis excludes embedded image/base64 payloads from its textual
  reconciliation prompt; independent VISION worker evidence is retained instead.
- A provider 4xx is reported as a failed orchestration attempt, never as a
  successful empty semantic result. HTTP 429 becomes a bounded admission
  deferral only when the positive integer `Retry-After` header exactly matches
  `error.detail.retry_after_seconds`; malformed or conflicting responses fail
  closed.
- An empty seed model is expanded from the configured gateway `/v1/models`
  endpoint; embedding-only rows are not added to the chat agent pool.
- Chat Completions and Responses may constrain routing to an exact configured
  endpoint identity; the selector is never forwarded to a provider and is not
  applied to embeddings or deferred batch work.
- A batch embedding request may omit `model`; contextual-orchestrator selects
  an embedding-capable model and returns its identity for subsequent batches.
- `json_object`, `json_schema`, and Responses JSON formats run conduct plus
  synthesis. Tool requests never silently fall back to one agent.
- Asynchronous provider-readiness jobs declare the positive integer polling
  cadence derived from the server's configured admission window; consumers do
  not invent a polling interval.

## Consequences

- Local Compose runtime and the reviewed upstream PR use the same orchestrator
  implementation.
- Rebuilding the image is required after the upstream pin changes.
- Updating the upstream pin or an OpenTelemetry root requires review of the
  new archive digest and regeneration of the complete hash lock.
- Protected-branch review and merge remain external gates; this pin does not
  bypass upstream review.

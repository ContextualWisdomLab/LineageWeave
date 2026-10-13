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
commit `8e1f1a8bf3e96e56dc8fcc90ec777883a1d56ce6`. The prior `1a40e0f7ad10d1a24137d69d20e44fc9a5dcdd89` pin is superseded.
The pin remains explicit and immutable until the protected-main change is superseded; it is not a
moving `main` reference and it is not a LineageWeave monkey patch.

The runtime contract is:

- LineageWeave may send `reasoning_effort="auto"` to the orchestrator.
- contextual-orchestrator resolves `auto` using its capability/routing policy.
- Only an explicit supported effort is sent to an upstream provider.
- Structured output uses provider-native final synthesis inside
  contextual-orchestrator and validates the requested `json_object` or
  `json_schema` contract locally; it is not a provider passthrough.
- This negotiation preserves multi-agent worker and synthesis calls and never
  collapses a structured request to a single-agent passthrough.
- Multimodal synthesis excludes embedded image/base64 payloads from its textual
  reconciliation prompt; independent VISION worker evidence is retained instead.
- A provider 4xx is reported as a failed orchestration attempt, never as a
  successful empty semantic result.
- An empty seed model is expanded from the configured gateway `/v1/models`
  endpoint; embedding-only rows are not added to the chat agent pool.
- A batch embedding request may omit `model`; contextual-orchestrator selects
  an embedding-capable model and returns its identity for subsequent batches.
- `json_object`, `json_schema`, and Responses JSON formats run conduct plus
  synthesis. Tool requests never silently fall back to one agent.

## Consequences

- Local Compose runtime and the reviewed upstream PR use the same orchestrator
  implementation.
- Rebuilding the image is required after the upstream pin changes.
- Protected-branch review and merge remain external gates; this pin does not
  bypass upstream review.

## 2026-10-03 candidate runtime repair

The historical image encodes the entire `response_format` envelope as a prompt
output contract. A provider can consequently return that envelope instead of
the schema instance. Use the protected-main implementation at immutable commit
`8e1f1a8bf3e96e56dc8fcc90ec777883a1d56ce6` as the candidate: native final
structured synthesis follows conducted evidence, locally validates JSON Schema,
and traces governed same-candidate repair and distinct eligible fallback. This
is a protocol-correctness change, not a new model-selection policy. ADR 0076
and upstream ADR 0035 remain governing; Fugu, TRINITY and Conductor are not
interpreted as authority for provider-name ranking or a new quality threshold.

Build from the checksum-verified immutable source archive and its complete
`requirements.lock` with `--require-hashes`; build both upstream native token
packing and decision-receipt extensions with the pinned Rust toolchain and
`Cargo.lock`. Do not approximate main using an older host virtual environment.
Keep source, Python lock, Cargo lock, image and installed dependency hashes in
private nonsecret execution receipts. No source monkey patch is permitted.

The updated upstream public-bind entrypoint requires distinct admin/inference
credentials resolved from the process credential registry. Treat the existing
`CONTEXTUAL_ORCHESTRATOR_TOKEN` as inference-only; bootstrap a separate ephemeral
admin credential and pass only registry names on argv. Register the approved
provider-host allowlist at bootstrap. No new provider credential is issued.

The candidate is isolated on host loopback and is not rollout authorization.
Ordinary chat and strict-schema provider requests are separate acceptance gates.
Embeddings, VISION, streaming, tools, complete-suite/security/review and parent
stack adoption remain separate obligations. Open PRs #1264, #1265 and #1346
are not protected-main delivery and are not silently transplanted into this pin.

The protected-main pip export omits the Linux/aarch64 NumPy wheel hash while
its canonical `uv.lock` includes that exact wheel. Retain the original lock
unchanged for provenance; export canonical `uv.lock` without re-resolution (`--frozen`)
and install that complete runtime export with required hashes and binary-only
packages. This avoids an unpinned NumPy build-backend install and preserves
canonical uv-lock dependency versions (some differ from the older pip export). Native CO extensions still build from Cargo.lock.

### Startup readiness follow-up (Rejected predecessor; replacement Proposed)

The earlier private candidate imposed ten seconds and sixteen workers on startup
probes. Independent review reproduced JSON-null sampling siblings, swallowed
HTTPError ownership, a twelve-second slow-trickle success despite the purported
ten-second bound, and executor shutdown requiring a forced kill. The original
negative verdict is retained; focused green tests did not approve this candidate.
Those constants also affected model admission, so the earlier assertion that
they were policy-neutral was incorrect. They are withdrawn, not renamed.

Upstream ADR 0032 prohibits default wall-clock deadlines for discovery, DNS,
connect, warm-up and inference; Proposed ADR 0127 provides no automatic timeout
allocator, while distinguishing independently configured audited admin state.
The isolated successor restores serial capability probing with no added
probe-specific deadline. Its registered transport calls propagate explicit
cancellation rather than reporting unsupported capability, and consumed HTTP
errors are closed. This does not establish complete-catalog discovery or
cancellation across every discovery worker. Failed proof does not establish
that a model lacks structured support. No new operator bound or fanout is
selected here.

This mechanical change does **not** solve whole-catalog startup availability:
upstream ADR 0015 still requires structured proof before row activation, and
serial unbounded startup can keep HTTP unavailable indefinitely. Upstream must
choose and review either asynchronous pending-row readiness with cancellable
refresh and last-known-good retention, or actual audited operator-supplied
admission bounds without repository defaults. The candidate has no availability
SLO, and its whole-discovery cancellation contract remains unverified. No
official deployment is authorized by this record.

The 2026-10-04 complete-source review also found that actual catalog discovery
still inherits a thirty-second deadline. Its daemon worker handoff does not
propagate the cancellation context, and generic discovery transports are not
registered with the probe transport owner. The direct-resolver cancellation
fixture bypasses that handoff. Inner DNS workers can outlive caller cancellation
until the system resolver returns. These are unresolved upstream defects, not
permission to choose another timeout or fanout. The historical 1,042.76-second
observation measured the first successful health response, not authenticated
readiness. Sampling and installed-source equality do not clear these defects.

Sampling omission is enforced at generated Chat, stream, structured judge,
Responses and batch bodies: explicit call overrides request scope, request scope
overrides administrator setting, and absent values are omitted, never JSON null.
The successor also carries sampling scope into streamed Responses; the judge
must not read a global client temperature instead of the request. The source is
an isolated upstream candidate, not code vendored or monkey-patched by LW.
The repository Dockerfile remains the immutable protected-main base under ADR
0070; a private diagnostic build must pin that base by digest, copy the complete
candidate subtree and current bootstrap, and bind every byte in its manifest.
It is not a released LW build until upstream protected review and immutable pin.

Bootstrap deletes keys from Python's `os.environ` and passes registry names on
argv. It does not erase the kernel's initial process environment, Docker container
configuration, registry memory or bootstrap locals. The host user, Docker daemon
and privileged process-memory readers are trusted. A clean-environment re-exec or
secret-file/pipe bootstrap with external registry custody needs a separate reviewed
threat-boundary decision; do not claim either is implemented. Compose publishes
the orchestrator only on host loopback, supplies private inference credential and
provider-host allowlist from `env_file` without an overriding default, and rejects
the known public development token. Backend credential alignment remains an
operator/bootstrap responsibility; this change does not print private config.

Open upstream PRs #1000, #1346, #1264 and #1265 were inspected incrementally, not
transplanted. Their unmerged decisions do not confer authority on this candidate.
Static role-fit/priority/cosine selection, automatic triage admission, existing
judge thresholds/rubric/calibration and tool workflow conflicts remain release
blockers under ADR 0076. Plain/strict JSON/product-client successes prove only
executed transport/schema/lineage seams, not calibrated quality. The same
independent reviewer must assess the final union of CO source, image, bootstrap,
Compose, tests and this record; the predecessor FAIL cannot be superseded by
self-review or synthetic tests alone.

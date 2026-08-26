# ADR 0218: MCP Global Ask submits and reads the durable current Ask contract

## Status

Accepted

## Context

The protected product exposes Global Ask as a durable asynchronous job. Its
current contract includes account and process-unit scope snapshots, revocation
intersection, evidence-constrained semantic rewriting, explicit public-claim
verification opt-in, retained revisions at a knowledge cutoff, limitations,
and provenance-bearing citations. Historical MCP work implemented a separate
synchronous Ask pipeline on a non-default stack. Reintroducing that pipeline
would let REST and MCP disagree about authorization, time, retrieval, and
verification.

Remote MCP clients also cross a distinct Streamable HTTP trust boundary. The
MCP transport specification requires Origin validation to prevent DNS
rebinding. OAuth protected-resource metadata and audience-restricted tokens
prevent a token issued for one resource from becoming authority at another.
Browser preflight and request-body admission must therefore happen before
OAuth, JSON parsing, database acquisition, quota consumption, or tool
invocation.

## Decision

1. LineageWeave exposes two MCP tools over Streamable HTTP:
   `submit_global_ask` queues the same durable job as `POST /api/ask`, and
   `read_global_ask_job` returns the same owner-scoped state and settled payload
   as `GET /api/ask/jobs/{id}`. MCP does not recreate answer computation.
2. Submission accepts `question`, `verify_external`, and optional
   `knowledge_cutoff`. Shared application-service functions own blank-question,
   permission, orchestrator-availability, ISO-8601, database-clock, scope
   snapshot, and enqueue behavior for both transports.
3. Reading preserves the stored answer payload without a second semantic,
   citation, public-verification, or cutoff interpretation. Another account's
   job remains indistinguishable from an absent job.
4. Keyverse issues an MCP-resource audience. The resource server validates
   issuer, signature, expiry, audience, required scope, and the existing
   provisioned LineageWeave account/affiliation contract before a tool runs.
   OAuth protected-resource metadata follows RFC 9728 and advertises this exact
   resource identifier.
5. An outer admission boundary validates Host and every present Origin,
   answers only exact configured browser preflights, rejects ambiguous or
   oversized framing while streaming, and replays admitted bytes once. It
   exposes browser-readable MCP session/protocol and `WWW-Authenticate`
   headers. No-Origin non-browser clients remain supported.
6. A shared Valkey counter consumes one quota unit only after token and
   provisioned-account resolution. The key contains a SHA-256 account digest,
   never a bearer token or display identifier. Limiter failure is explicitly
   unavailable; it never falls back to a process-local counter. The request
   limit and window are mandatory positive deployment inputs established by
   measured capacity policy, not library defaults. Exhaustion returns the
   actual bounded window remainder in structured MCP data and `Retry-After`.
7. MCP runs as a dedicated Compose service and reuses the existing PostgreSQL,
   Valkey, Keyverse, contextual-orchestrator, semantic retrieval, and worker
   boundaries. It does not add a database, provider call, model selector, or
   LineageWeave-local scheduler.

## Consequences

- REST, MCP, UI polling, reports, and alerts read one persisted answer contract.
- MCP submission remains responsive while multi-minute orchestration stays in
  the existing worker.
- Preflight, hostile transport metadata, malformed framing, and oversized
  bodies cannot consume authentication, database, worker, or quota capacity.
- Deployment must supply an evidence-backed quota policy; missing policy fails
  startup instead of silently choosing a rule of thumb.
- The historical MCP stacks remain reusable implementation evidence, not
  protected-main delivery or a second product contract.

## References

Campbell, B., Bradley, J., & Tschofenig, H. (2020). *Resource indicators for
OAuth 2.0* (RFC 8707). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8707

Jones, M., Hunt, P., & Parecki, A. (2025). *OAuth 2.0 protected resource
metadata* (RFC 9728). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9728

Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). *Best current
practice for OAuth 2.0 security* (RFC 9700). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9700

Model Context Protocol. (2025). *Transports: Streamable HTTP* (Specification
2025-06-18).
https://modelcontextprotocol.io/specification/2025-06-18/basic/transports


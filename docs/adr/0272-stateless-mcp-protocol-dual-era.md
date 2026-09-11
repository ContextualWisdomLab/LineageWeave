# ADR 0272: Serve the current stateless MCP protocol beside the legacy handshake era

**Status:** Proposed
**Date:** 2026-09-11
**Amends:** [ADR 0218](0218-current-contract-mcp-global-ask.md)

## Context

ADR 0218 accepted a dedicated Streamable HTTP MCP resource server whose
transport contract followed the handshake era: `initialize` /
`notifications/initialized`, an `Mcp-Session-Id` for every follow-up request,
and no per-request routing metadata. The pinned official Python MCP SDK
`mcp==2.0.0` (released 2026-07-28) implements a newer revision from the same
`streamable_http_app()`: the 2026-07-28 specification removes protocol-level
handshake and session state, makes every request self-describing through
`params._meta` protocol and capability entries, adds optional
`server/discover`, and requires `Mcp-Method` and, for name-bearing methods,
`Mcp-Name` request headers over Streamable HTTP. Requests carrying a
handshake-era `MCP-Protocol-Version` still route to the legacy path.

LineageWeave's executable acceptance tooling still hard-coded the 2025-11-25
handshake path, so the product could not demonstrate that the current protocol
reaches the same durable Global Ask tools. Browser clients were also blocked
before OAuth: the admission boundary's CORS allow-list omitted `Mcp-Method`
and `Mcp-Name`, so a standards-compliant preflight for the modern headers was
not answered even though the SDK server would have served the request.

The SDK is the protocol implementation owner. This increment configures the
released boundary and proves both eras; it does not fork protocol parsing or
routing into LineageWeave.

## Decision

1. The MCP resource server serves the 2026-07-28 stateless revision and the
   handshake revisions the pinned SDK routes, from the same application.
   `server/discover` reports the supported revisions; modern requests are
   validated per request and need no `Mcp-Session-Id`.
2. The pre-auth admission boundary's CORS allow-list includes `Mcp-Method`
   and `Mcp-Name` beside the existing `MCP-Protocol-Version` and
   `Mcp-Session-Id`. No origin, Host, audience, scope, body-framing, or quota
   rule changes; a mismatched `Mcp-Method` or `Mcp-Name` still fails closed
   before any tool invocation or quota consumption.
3. `scripts/k6_mcp_e2e.js` exercises the modern stateless lane by default —
   `MCP_PROTOCOL_VERSION` defaults to `2026-07-28`, every `tools/call` is
   self-contained, carries the `_meta` protocol version, client capabilities,
   and explicit `clientInfo` identity plus the routing headers, and carries no
   session — and retains the 2025-11-25 handshake lane as an explicitly named
   compatibility selection through the same script. The harness attributes a
   reply to an observation only when `jsonrpc` and the request `id` match and
   exactly one of `result` / `error` is present; response content never reaches
   diagnostics.
4. The isolated modern lane, the legacy lane, the fail-closed routing-header
   mismatch, and the browser preflight are covered by contract tests; the
   load harness measures the same authenticated durable Global Ask submit/read
   buyer path as before. Multi-minute Global Ask orchestration stays in the
   existing worker and outside transport latency.
5. Global Ask semantics, the shared application-service delegation, Keyverse
   audience/scope, protected-resource metadata, PostgreSQL evidence
   authorization, Valkey quota, and the contextual-orchestrator boundary all
   remain as accepted in ADR 0218.
6. Legacy sessions are worker-local SDK state. A multi-worker deployment that
   keeps the handshake-era lane must preserve affinity for follow-up requests
   carrying the same `Mcp-Session-Id`; otherwise a different worker can reject
   a valid legacy session as unknown. Deployments that instead select the SDK's
   stateless HTTP mode do not mint those sessions, but must treat features that
   depend on session state or server-to-client back-channel state as unavailable.

## Consequences

- A modern MCP client that sends no handshake and no session identifier can
  discover the server and call both Global Ask tools; two sequential modern
  calls are served independently without sticky routing.
- A handshake-era client keeps initializing, receiving `Mcp-Session-Id`, and
  calling the same tools during the upstream deprecation window. In a
  multi-worker deployment, those follow-up requests require session affinity
  unless the deployment deliberately chooses the SDK's stateless mode and its
  reduced session-dependent feature set.
- Browser clients can preflight the modern routing headers; the admitted
  request still crosses the same OAuth, body-admission, and quota order.
- The load lane no longer names the legacy handshake the current protocol;
  legacy compatibility is an explicit, separately selectable regression.
- Interoperability evidence for the modern lane is an isolated synthetic
  observation, not a production capacity claim.

## Alternatives considered

- **Hand-rolling a LineageWeave-local modern protocol router.** Rejected:
  duplicates released SDK behavior, creates a protocol-version drift surface,
  and contradicts ADR 0218's reuse boundary.
- **Dropping the legacy lane to simplify the harness.** Rejected: the issue
  requires older clients to keep working through the deprecation window, and
  the dual-era behavior lives in the SDK rather than in a fork.
- **Broadening CORS origins instead of naming the headers.** Rejected: it
  weakens the admission boundary without serving the standard; only the two
  routing headers are added.

## References

Model Context Protocol. (2025). *Transports: Streamable HTTP* (Specification
2025-06-18).
https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

Model Context Protocol. (2026, July 28). *The 2026-07-28 specification*.
https://blog.modelcontextprotocol.io/posts/2026-07-28/

Model Context Protocol Python SDK. (2026). *What's new in v2: The protocol:
2025-11-25 to 2026-07-28*.
https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md

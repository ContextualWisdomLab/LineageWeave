# ADR 0119: MCP browser and request-byte admission precede OAuth

- **Status:** Accepted
- **Date:** 2026-08-20
- **Extends:** ADR 0031

## Context

ADR 0031 establishes an authenticated Streamable HTTP MCP resource server with
Host and Origin validation. A browser client adds two concrete transport
requirements that a non-browser MCP client does not:

1. an authenticated cross-origin POST commonly requires an unauthenticated
   CORS preflight; and
2. the request body can arrive without a trusted `Content-Length`, so a limit
   checked only after SDK JSON parsing is not a resource boundary.

If preflight reaches OAuth first, the browser cannot complete the request even
when its exact Origin is allowed. If the OAuth `WWW-Authenticate` challenge is
not exposed, browser JavaScript also cannot read the protected-resource
metadata needed for discovery. If the server relies only on a declared length,
a chunked or otherwise streamed body can allocate and decode more data than the
intended MCP request envelope. Ambiguous `Content-Length` and
`Transfer-Encoding` combinations create inconsistent framing boundaries.

The MCP Streamable HTTP specification requires Origin validation on incoming
connections to prevent DNS rebinding. RFC 9112 defines request framing and
identifies `Content-Length` plus `Transfer-Encoding` as a request-smuggling
risk. The Fetch CORS protocol requires an Origin-sensitive response contract
for browser access.

## Decision

1. Keep MCP SDK Host and Origin validation as the outermost HTTP boundary.
   A hostile Host returns `421`; an invalid present Origin returns `403` before
   OAuth, database access, MCP parsing, or a tool invocation.
2. Handle an exact allowed-Origin CORS preflight outside OAuth. Never use `*`,
   suffix matching, prefix matching, credentials, or Origin reflection.
   Configured Origins must be exact HTTP(S) origins without credentials, path,
   query, or fragment; an unsafe entry prevents process startup.
3. Limit the browser contract to the Streamable HTTP methods used by the SDK:
   `GET`, `POST`, and `DELETE`. Permit only the request headers needed by MCP
   and OAuth: `Accept`, `Authorization`, `Content-Type`, `Last-Event-ID`,
   `MCP-Protocol-Version`, and `Mcp-Session-Id`.
4. Expose only `MCP-Protocol-Version`, `Mcp-Session-Id`, and
   `WWW-Authenticate` to browser clients. The first two carry the MCP transport
   contract; the last lets an allowed client read OAuth protected-resource
   discovery. Origin-sensitive responses include `Vary: Origin`.
5. Preserve non-browser clients: a request without `Origin` remains valid and
   reaches the existing OAuth boundary.
6. Place a pure-ASGI body admission wrapper after Host/Origin validation and
   before CORS, OAuth, or SDK JSON parsing for every POST.
7. Use `Content-Length` only for an early rejection. Independently count every
   received body chunk and stop once the configured byte limit would be
   exceeded.
8. Reject negative, nondecimal, non-ASCII, duplicate `Content-Length`, and a
   request carrying both `Content-Length` and `Transfer-Encoding`. Reject a
   declared/actual length mismatch. The stricter duplicate policy is deliberate:
   LineageWeave does not need intermediary-compatible normalization at this
   application boundary.
9. Accept a body without `Content-Length` when the actual streamed bytes remain
   bounded. Replay an admitted body byte-for-byte exactly once to the SDK.
10. Use a default `MCP_MAX_REQUEST_BYTES` of 65,536 bytes. Operators may choose
    8,192 through 1,048,576 bytes; invalid values prevent process startup.
11. Return stable payload-safe admission errors without echoing request bytes:
    `mcp_invalid_content_length`, `mcp_content_length_mismatch`,
    `mcp_request_disconnected`, `mcp_invalid_request_body`, and
    `mcp_request_too_large`. Admission errors are `Cache-Control: no-store`.
12. Keep distributed per-principal invocation limiting separate. A pre-auth
    byte or CORS rejection must not consume an invocation quota, and a future
    MCP-compatible rate-limit response must not be fabricated at this transport
    boundary.

The effective request path is:

```text
Host/Origin transport validation
→ bounded POST body admission
→ exact CORS/preflight handling
→ OAuth resource-server middleware
→ MCP SDK JSON parsing and routing
→ database RBAC/ABAC
→ Global Ask
```

## Consequences

- Browser MCP clients can complete preflight and read the OAuth discovery
  challenge without weakening exact-Origin validation.
- Fixed-length and streamed requests share one byte envelope before expensive
  parsing or authentication work.
- A valid request is buffered once at the MCP ingress. The configured upper
  bound makes that memory cost explicit and finite.
- Reverse proxies should still reject malformed framing and close unsafe
  HTTP/1.1 connections. This application boundary is defense in depth, not a
  replacement for correct proxy framing.
- The endpoint remains usable by Codex and other non-browser clients that omit
  `Origin`.

## Rejected alternatives

- **OAuth before CORS:** makes an otherwise authorized browser integration
  unusable because preflight has no bearer token.
- **Wildcard CORS:** permits arbitrary websites to address the protected MCP
  resource and defeats the exact-Origin contract.
- **Document-only exact-Origin rules:** leave an operator able to configure a
  wildcard or non-origin URL and silently weaken the runtime boundary.
- **Trust `Content-Length` only:** does not bound a streamed body and cannot
  defend against header/body disagreement.
- **Require `Content-Length` on every request:** unnecessarily rejects valid
  bounded HTTP streaming clients.
- **Call `request.json()` and then check size:** performs the allocation and
  decoding before enforcing the resource boundary.
- **Fold rate limiting into pre-auth admission:** lacks an authenticated
  principal and would mix transport abuse controls with billable tool quota.

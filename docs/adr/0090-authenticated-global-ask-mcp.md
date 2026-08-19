# ADR 0090: Authenticated Global Ask MCP resource server

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave already has an authenticated buyer-facing Global Ask flow (`POST /api/ask`) that assembles a bounded evidence set only after the caller's `post_read` RBAC and per-row corporate-entity ABAC checks. The answer is produced only through `contextual-orchestrator`, and citations identify the source posts used by the answer (ADR 0039).

External agent clients such as Codex need the same capability without receiving database credentials or a privileged service token and without bypassing the existing evidence boundary. A remote MCP server also creates a distinct OAuth protected-resource boundary: the access token must be intended for the MCP server itself, browser origins must not be able to reach a local/remote endpoint through DNS rebinding, and an inbound bearer token must not be forwarded to another API.

The currently accumulated Buyer stack also contains two independent blockers that this ADR does not hide or override: PR #258 has an unresolved static-analysis review thread, and PR #264 has an unresolved review finding that DAG navigation can discard analysis-run cutoff context. This MCP slice is stacked on #264 and must not merge ahead of its prerequisite chain.

## Decision

LineageWeave exposes a **separate FastAPI MCP resource server** at `backend.app.mcp_server:app` rather than adding MCP transport behavior to the browser-facing application.

The first MCP surface contains exactly one tool:

```text
global_ask(question)
```

The tool is read-only and returns:

- grounded answer text;
- cited post identifiers and display summaries;
- citation evidence;
- the bounded set of source post identifiers considered;
- an explicit next action when no authorized evidence exists.

The MCP server reuses the same Global Ask source assembler and the same `ContextualOrchestratorPostChatClient`. It does **not** forward the MCP access token to contextual-orchestrator or call the browser REST endpoint with that token.

### Protocol profile

The initial server implements MCP protocol revision `2025-06-18` over non-streaming Streamable HTTP:

- JSON-RPC 2.0;
- `initialize` and `notifications/initialized` lifecycle messages;
- `ping`;
- `tools/list`;
- `tools/call`;
- one POST endpoint at `/mcp`;
- GET `/mcp` returns 405 because this slice does not offer SSE;
- JSON-RPC batching is rejected;
- tool output includes both `structuredContent` and a JSON text content block;
- the `global_ask` tool advertises `readOnlyHint=true`, `destructiveHint=false`, and `openWorldHint=false`.

### OAuth protected-resource boundary

The MCP process is an OAuth protected resource, not an authorization server.

It publishes RFC 9728 protected-resource metadata and advertises the configured LineageWeave/Keyverse OIDC issuer as its authorization server. The canonical resource identifier is configured by `LINEAGEWEAVE_MCP_RESOURCE_URI` and must identify the `/mcp` resource.

Every protected request must satisfy all of the following before evidence is touched:

1. Bearer authentication is present.
2. JWT `kid` is non-empty and exactly selects one acceptable RSA/RS256 JWKS key; no first-key fallback is allowed.
3. Signature, issuer, expiry/not-before semantics, and configured clock skew validate.
4. JWT audience includes the exact MCP resource URI.
5. `sub` resolves to a provisioned `user_account`.
6. roles stored in LineageWeave grant `post_read`.
7. corporate-entity affiliations are loaded from LineageWeave, not trusted from arbitrary token claims.
8. each source post still passes the product's per-row ABAC predicate before normalization or LLM context assembly.

A 401 challenge includes the RFC 9728 `resource_metadata` location. The MCP access token is never passed through to downstream APIs.

### Origin and transport policy

When an HTTP `Origin` header is present it must exactly match `LINEAGEWEAVE_MCP_ALLOWED_ORIGINS`; an unknown browser origin fails closed. Non-browser MCP clients may omit `Origin`.

Production deployment must use an HTTPS canonical resource. Plain HTTP is reserved for loopback development only. The MCP service is independently deployable so its ingress, OAuth audience, rate policy, network policy, and telemetry can be isolated from the Buyer web application.

### Bounds and audit

- Questions are limited to 4,000 characters.
- The existing Global Ask bounded-source contract remains in force.
- Tool calls are rate-limited per authenticated account. The first implementation is process-local; a later horizontally scaled slice must replace this with a shared counter before multiple MCP replicas are enabled.
- Audit logging records only opaque account id, question length, number of considered sources, and citation count. Question text, answer text, bearer token, and raw post bodies are not emitted to the MCP audit log.

## Consequences

- Codex and other conforming MCP clients can authenticate to a dedicated LineageWeave resource and invoke Global Ask without obtaining database or orchestrator credentials.
- The tool cannot expand the caller's evidence visibility beyond the existing `post_read` + ABAC contract.
- A browser login token minted only for the frontend is not automatically valid for MCP: Keyverse must issue a resource-bound access token whose audience includes the configured MCP resource URI.
- No write tools, arbitrary SQL, raw graph traversal, admin actions, ticket changes, analysis-run starts, or unrestricted post-body resources are exposed in this slice.
- Horizontal MCP scaling is blocked until distributed rate limiting is implemented.
- This ADR does not cure the browser application's separate audience-validation weakness or the #264 temporal-cutoff navigation defect. Those remain prerequisite-stack work and must not be treated as satisfied by the MCP-specific verifier.

## References

See `docs/doctoring/MCP_REFERENCES.md` for the normative protocol and OAuth references in APA 7th format.

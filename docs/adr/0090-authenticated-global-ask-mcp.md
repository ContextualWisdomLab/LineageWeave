# ADR 0090: Authenticated Global Ask MCP resource server

- Status: Accepted
- Date: 2026-08-20

## Context

LineageWeave already has an authenticated buyer-facing Global Ask flow (`POST /api/ask`) that assembles a bounded evidence set only after the caller's `post_read` RBAC and per-row corporate-entity ABAC checks. The answer is produced only through `contextual-orchestrator`, and citations identify the source posts used by the answer (ADR 0039).

External agent clients such as Codex need the same capability without receiving database credentials or a privileged service token and without bypassing the existing evidence boundary. A remote MCP server creates a distinct OAuth protected-resource boundary: the access token must be intended for the MCP resource itself, browser origins must not be able to reach it through an unrelated origin, and an inbound bearer token must not be forwarded to another API.

The accumulated Buyer stack contains independent blockers that this ADR does not hide or override: PR #258 has an unresolved static-analysis review thread, and PR #264 has an unresolved review finding that DAG navigation can discard analysis-run cutoff context. This MCP slice is stacked on #264 and must not merge ahead of its prerequisite chain.

## Decision

LineageWeave exposes a **separate FastAPI MCP resource server** at `backend.app.mcp_server:app` rather than adding MCP transport behavior to the browser-facing application.

The first MCP surface contains exactly one tool:

```text
global_ask(question)
```

The tool is read-only and returns grounded answer text, cited post identifiers and summaries, citation evidence, the bounded source set considered, and an explicit next action when no authorized evidence exists. It reuses the same Global Ask source assembler and `ContextualOrchestratorPostChatClient`. It does **not** forward the MCP access token to contextual-orchestrator or call the Buyer REST endpoint with that token.

### Protocol profile

The server targets the current MCP protocol revision `2026-07-28` over stateless Streamable HTTP.

- There is no `initialize`/`initialized` handshake and no `Mcp-Session-Id`.
- Each request carries the protocol revision and client capabilities in `params._meta`.
- Clients may call `server/discover` to learn the supported revision and capabilities.
- Every POST requires `MCP-Protocol-Version` and `Mcp-Method`; `tools/call` additionally requires `Mcp-Name` matching `params.name`.
- Header/body mismatches fail with `HeaderMismatch` (`-32020`); unsupported revisions fail with `UnsupportedProtocolVersion` (`-32022`).
- `tools/list` returns deterministic tool definitions with explicit `ttlMs=0` and `cacheScope=private`.
- Successful 2026-era results carry `resultType=complete` and `_meta.io.modelcontextprotocol/serverInfo`.
- `global_ask` advertises `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, and `openWorldHint=false`.
- JSON-RPC batching is rejected. No subscription stream or MRTR flow is needed for this first read-only tool.

### OAuth protected-resource boundary

The MCP process is an OAuth protected resource, not an authorization server. It publishes RFC 9728 protected-resource metadata and advertises the configured LineageWeave/Keyverse OIDC issuer. `LINEAGEWEAVE_MCP_RESOURCE_URI` is the canonical resource identifier.

Every protected request must satisfy all of the following before evidence is touched:

1. Bearer authentication is present.
2. JWT `kid` is non-empty and exactly selects one acceptable RSA/RS256 JWKS key; there is no first-key fallback.
3. Signature, issuer, expiry/not-before semantics, and bounded clock skew validate.
4. JWT audience includes the exact MCP resource URI.
5. `sub` resolves to a provisioned `user_account`.
6. persisted roles grant `post_read`.
7. corporate-entity affiliations are loaded from LineageWeave, not trusted from token-side business claims.
8. each source still passes the product's row-level ABAC predicate before normalization or LLM context assembly.

A 401 challenge includes the RFC 9728 `resource_metadata` location. The bearer token is never passed through to downstream APIs. The authorization client/issuer side must also follow the 2026-07-28 authorization hardening, including issuer validation and the migration away from Dynamic Client Registration toward Client ID Metadata Documents where supported.

### Origin, transport, bounds, and audit

When an HTTP `Origin` header is present it must exactly match `LINEAGEWEAVE_MCP_ALLOWED_ORIGINS`; an unknown browser origin fails closed. Non-browser clients may omit `Origin`. Production resource identifiers must use HTTPS; plain HTTP is accepted only for loopback development.

Questions are limited to 4,000 characters. Tool calls use the existing Valkey service for a distributed fixed-window per-account rate limit, preserving the stateless/horizontally scalable MCP request model. Audit logging records only opaque account id, question length, considered-source count, and citation count; question text, answer text, bearer tokens, and source bodies are not logged by the MCP audit path.

## Consequences

- Codex and other conforming MCP clients can authenticate to a dedicated LineageWeave resource and invoke Global Ask without database or orchestrator credentials.
- The tool cannot expand evidence visibility beyond `post_read` plus the existing ABAC contract.
- A frontend login token is not automatically an MCP token: the authorization server must mint a token for the exact MCP resource audience.
- No write tools, arbitrary SQL, unrestricted graph traversal, admin actions, ticket changes, analysis-run starts, or unrestricted post-body resources are exposed.
- The MCP request path is stateless across replicas; only authorization/evidence data in PostgreSQL and bounded rate counters in Valkey are shared.
- This ADR does not cure the Buyer application's separate audience-validation weakness or #264 temporal-cutoff navigation defect. Those remain prerequisite-stack work.

## References

See `docs/doctoring/MCP_REFERENCES.md` for normative protocol and OAuth references in APA 7th format.

# LineageWeave MCP server

LineageWeave exposes the Buyer Global Ask workflow as a separately deployable, authenticated MCP resource server.

## Surface

The first release exposes one read-only tool:

```text
global_ask(question)
```

It uses the same persisted `post_read` permission, per-post corporate-entity ABAC predicate, bounded Global Ask source assembler, evidence, and contextual-orchestrator answer channel as the Buyer product. It does not expose SQL, unrestricted post bodies, admin operations, tickets, analysis-run writes, or arbitrary graph queries.

## Protocol

The server targets **MCP 2026-07-28**. The protocol core is stateless: there is no `initialize` handshake or protocol session. Clients may probe `server/discover`; every request otherwise stands alone.

Every POST must carry:

```text
MCP-Protocol-Version: 2026-07-28
Mcp-Method: <JSON-RPC method>
```

`tools/call` also carries:

```text
Mcp-Name: global_ask
```

The JSON body carries the same protocol version and client capabilities in `params._meta`. LineageWeave rejects header/body mismatches and unsupported protocol revisions. `tools/list` returns `ttlMs=0` and `cacheScope=private`; successful responses include `resultType=complete` and server identity in result `_meta`.

## Run locally

```bash
uv sync --frozen --extra backend --extra dev
uv run uvicorn backend.app.mcp_server:app --host 127.0.0.1 --port 18421
```

Local development endpoints:

```text
MCP endpoint: http://localhost:18421/mcp
Protected-resource metadata: http://localhost:18421/.well-known/oauth-protected-resource/mcp
```

Production must publish an HTTPS MCP resource URI and configure the authorization server to issue access tokens whose audience includes that exact resource URI.

## Configuration

```text
LINEAGEWEAVE_MCP_RESOURCE_URI
- canonical OAuth resource identifier
- local default: http://localhost:18421/mcp
- HTTPS required outside loopback development

LINEAGEWEAVE_MCP_ALLOWED_ORIGINS
- comma-separated exact browser Origins permitted to reach /mcp
- empty means requests carrying Origin are rejected
- non-browser clients may omit Origin

LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE
- distributed per-account tool-call limit stored in existing Valkey
- default 30, allowed range 1..600
```

The MCP verifier additionally requires a non-empty exact RSA/RS256 JWT `kid`, matching issuer, matching MCP resource audience, normal JWT time validation, a provisioned LineageWeave account, and persisted `post_read`. Corporate affiliations and permissions are loaded from PostgreSQL; token-side business attributes cannot widen evidence access.

## Authorization-server requirement

The MCP process is an OAuth protected resource, not an authorization server. It publishes RFC 9728 protected-resource metadata. The configured Keyverse/OIDC authorization server must support the MCP client authorization flow and mint a resource-bound access token for `LINEAGEWEAVE_MCP_RESOURCE_URI`.

If the authorization server has not been configured for that resource, MCP authentication must fail rather than accepting a frontend token by disabling audience verification. Authorization-client configuration should follow the current MCP 2026-07-28 issuer-validation and client-registration guidance.

## Codex

Configure Codex to connect to the externally reachable LineageWeave `/mcp` endpoint and complete the OAuth flow discovered through the protected-resource metadata. OpenAI's operational guidance allows MCP OAuth credentials to be stored in the operating-system keyring. Do not commit bearer tokens or place them in `AGENTS.md`.

The exact client registration belongs in Keyverse/identity configuration; do not add a Codex-specific authentication bypass to LineageWeave.

## Result contract

A successful tool call returns MCP text content plus `structuredContent`:

```json
{
  "answer_text": "...",
  "cited_post_ids": ["..."],
  "cited_posts": [{"post_id": "...", "post_title": "..."}],
  "cited_post_evidence": [{"post_id": "..."}],
  "source_post_ids": ["..."],
  "next_action": null
}
```

When no authorized source exists, the answer is empty and `next_action` explains that no authorized evidence is available. A missing or incomplete contextual-orchestrator result is a tool execution error; LineageWeave does not manufacture an answer.

## Security properties

- No inbound MCP bearer token is passed to contextual-orchestrator or the Buyer REST API.
- Authorization happens before source normalization and model context assembly.
- Browser Origin validation fails closed.
- Questions are bounded to 4,000 characters.
- The tool catalog contains no write tool.
- Valkey rate limiting works across MCP replicas without introducing MCP protocol session state.
- Audit logging records opaque account id and counts only, not question text, answer text, source bodies, or credentials.

## Stack prerequisites

This feature is stacked on PR #264. It does not permit bypassing existing review or merge gates. The accumulated Buyer stack must first resolve the #258 review blocker and #264 analysis-run cutoff propagation finding, then revalidate exact-head checks in stack order.

See ADR 0090 and `docs/doctoring/MCP_REFERENCES.md` for normative protocol and OAuth traceability.

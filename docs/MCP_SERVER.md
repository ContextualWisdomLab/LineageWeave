# LineageWeave MCP server

LineageWeave exposes the Buyer Global Ask workflow as a separately deployable, authenticated MCP resource server.

## Surface

The first MCP release intentionally exposes one tool only:

```text
global_ask(question)
```

It is read-only. It uses the same `post_read` permission, per-post corporate-entity ABAC predicate, bounded Global Ask source assembler, persisted evidence, and contextual-orchestrator answer channel as the Buyer product. It does not expose SQL, unrestricted post bodies, admin operations, tickets, analysis-run writes, or arbitrary graph queries.

## Run locally

Install the backend extra and start the MCP app independently from the Buyer API:

```bash
uv sync --frozen --extra backend --extra dev
uv run uvicorn backend.app.mcp_server:app --host 127.0.0.1 --port 18421
```

The local development defaults are:

```text
MCP endpoint: http://localhost:18421/mcp
Protected-resource metadata: http://localhost:18421/.well-known/oauth-protected-resource/mcp
```

Production must publish an HTTPS MCP resource URI and configure the authorization server to issue access tokens whose audience includes that exact resource URI.

## Configuration

```text
LINEAGEWEAVE_MCP_RESOURCE_URI
- canonical OAuth resource identifier for the MCP endpoint
- local default: http://localhost:18421/mcp
- production: externally reachable HTTPS /mcp URI

LINEAGEWEAVE_MCP_ALLOWED_ORIGINS
- comma-separated exact browser Origins permitted to reach /mcp
- empty means every request carrying an Origin header is rejected
- non-browser MCP clients may omit Origin

LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE
- per-account bounded tool-call rate
- default 30, allowed range 1..600
```

The existing LineageWeave OIDC variables select Keyverse or the explicit local Keycloak fallback. The MCP verifier additionally requires:

- a non-empty JWT `kid` that exactly selects an acceptable RSA/RS256 JWKS key;
- matching issuer;
- matching MCP resource audience;
- normal JWT time validation with the configured bounded clock skew;
- a provisioned LineageWeave `user_account`;
- persisted `post_read` permission.

Corporate affiliations and permissions are loaded from LineageWeave PostgreSQL. Untrusted token attributes cannot widen evidence access.

## Authorization-server requirement

The MCP server is an OAuth protected resource, not an authorization server. The configured Keyverse/OIDC authorization server must support the MCP client's authorization flow and issue a resource-bound access token for `LINEAGEWEAVE_MCP_RESOURCE_URI`. The MCP endpoint publishes RFC 9728 protected-resource metadata so a conforming client can discover the issuer.

If Keyverse has not yet been configured to issue an access token for that resource, MCP authentication must fail rather than accepting the ordinary frontend token by disabling audience verification.

## Codex

Codex supports remote MCP use and MCP OAuth credentials can be stored in the operating-system keyring. Configure Codex to connect to the externally reachable LineageWeave `/mcp` URL and complete the OAuth flow offered through the protected-resource metadata discovery path. Do not place bearer tokens in this repository or in an `AGENTS.md` file.

The exact Codex client-registration workflow depends on the authorization-server deployment. Keep client registration in Keyverse/identity configuration; do not add a Codex-specific authentication bypass to LineageWeave.

## Result contract

A successful `global_ask` tool call returns both MCP text content and `structuredContent`:

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

When no authorized source exists, the answer is empty and `next_action` explains that no authorized evidence is available. A missing or incomplete contextual-orchestrator result is an MCP tool execution error; LineageWeave does not manufacture an answer.

## Security properties

- No inbound MCP bearer token is passed to contextual-orchestrator or the Buyer REST API.
- Authorization happens before source normalization and model context assembly.
- Browser Origin validation prevents an unrelated web origin from reaching the MCP endpoint.
- Questions are bounded to 4,000 characters.
- The tool catalog is static and contains no write tool.
- The audit log records account id and counts only, not question text, answer text, source bodies, or tokens.
- This first rate limiter is process-local. Run a single MCP replica until a shared rate-limit backend is implemented.

## Stack prerequisites

This feature is stacked on PR #264. It is not permission to bypass existing review or merge gates. In particular, the accumulated Buyer stack must first resolve the #258 review blocker and #264 analysis-run cutoff propagation finding, then revalidate exact-head checks in stack order.

See ADR 0090 and `docs/doctoring/MCP_REFERENCES.md` for the normative protocol and OAuth traceability.

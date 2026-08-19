# LineageWeave MCP integration

LineageWeave exposes a dedicated **Streamable HTTP** Model Context Protocol
resource server at `/mcp`. It is a separate ASGI process from the product REST
API, but it reuses the same PostgreSQL source of truth, Keycloak/Keyverse issuer,
`post_read` permission, account affiliations, ABAC visibility rule, Event-Lineage
retrieval, content normalization, and contextual-orchestrator reason-and-cite
client.

## Tool contract

`global_ask(question)` is read-only, idempotent, and closed-world with respect to
LineageWeave state. It returns:

- `answer_text`
- the selected `anchor_post_id`
- `source_post_ids` for every bounded source passed to the reasoner
- `cited_post_ids` and `cited_posts`

The tool never promotes an inferred answer to an authoritative fact. Citation
IDs not present in the authorized source bundle are discarded; if no authorized
citation remains, the call fails instead of returning unsupported prose. No
Global Ask row is written merely because an MCP client asked a question.

The reason-and-cite call uses contextual-orchestrator's supported
`mode="conduct"` contract with high reasoning effort. It does not use the
rejected legacy `verify` mode and never falls back to a direct model provider.
The downstream call is bounded to 300 seconds so verified orchestration is not
prematurely cut off while remaining finite.

## Authentication and authorization

The MCP endpoint is an OAuth protected resource:

1. the bearer JWT signature is verified against issuer JWKS;
2. `iss`, expiry, mandatory exact `kid`, and the configured MCP `audience` are
   verified;
3. malformed JWKS structures fail closed;
4. optional `MCP_REQUIRED_SCOPES` are enforced by the MCP SDK;
5. the token `sub` must resolve to a provisioned `user_account`;
6. the account must have `post_read`;
7. every candidate and every lineage-expanded source is checked against the
   existing public-or-affiliated ABAC rule.

The inbound bearer token is never forwarded to contextual-orchestrator or any
other downstream service. Provider credentials remain service credentials.

### Required deployment settings

```text
MCP_RESOURCE_URL=https://lineage.example.com/mcp
MCP_AUDIENCE=https://lineage.example.com/mcp
MCP_ALLOWED_HOSTS=lineage.example.com
MCP_ALLOWED_ORIGINS=
MCP_REQUIRED_SCOPES=lineageweave:ask
```

The identity provider must issue access tokens whose `aud` includes the exact
`MCP_AUDIENCE`. The scope is optional at the product default because database
RBAC is mandatory regardless; production deployments should provision and
require `lineageweave:ask`.

DNS-rebinding protection is enabled. Do not disable it to make a deployment
work; add only the real public hostname and, for browser MCP clients, exact
allowed origins.

## Codex configuration

The guaranteed integration path uses a pre-issued short-lived bearer token in
an environment variable:

```toml
[mcp_servers.lineageweave]
url = "https://lineage.example.com/mcp"
bearer_token_env_var = "LINEAGEWEAVE_ACCESS_TOKEN"
required = true
enabled_tools = ["global_ask"]
default_tools_approval_mode = "writes"
tool_timeout_sec = 330
```

`global_ask` is annotated read-only, idempotent, and closed-world. Codex's
`writes` approval mode therefore continues to prompt for non-read-only tools
without misclassifying this evidence query as a write. The Codex timeout is set
slightly above LineageWeave's 300-second downstream bound so the server, not the
client, returns the actionable failure.

Interactive `codex mcp login lineageweave` can be enabled after Keyverse or
Keycloak has a Codex OAuth client-registration policy compatible with the MCP
authorization specification. The LineageWeave resource server already exposes
protected-resource metadata and validates the resulting audience-bound token;
client registration and exact callback-URI registration remain authorization-
server responsibilities.

## Local Compose

```bash
docker compose up --build postgres keycloak mcp
```

The default endpoint is `http://localhost:18001/mcp`. The demo realm adds that
exact audience to access tokens issued by `lineageweave-frontend`. A different
host or port requires a corresponding IdP audience and environment change; do
not accept the REST frontend audience as a substitute.

## Failure behavior

- untrusted Host: HTTP `421` before authentication
- no bearer or invalid bearer: HTTP `401`
- valid bearer without a required OAuth scope: HTTP `403`
- unprovisioned subject or missing `post_read`: tool error, no evidence returned
- no matching authorized evidence: tool error, no unrelated recent post fallback
- contextual-orchestrator unavailable, malformed, or uncited: tool error, no invented answer
- unknown citation ID: omitted; all-unknown citations fail the call

## Operational checks

A release must exercise the MCP SDK client against the in-process server, assert
tool annotations and structured output, verify Host and unauthenticated HTTP
rejection, and run the same auth, ABAC, source-boundary, citation, and
contextual-orchestrator mode regressions in the normal test suite. `uv.lock`
remains authoritative for the MCP SDK version.
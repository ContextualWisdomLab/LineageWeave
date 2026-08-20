# LineageWeave MCP integration

LineageWeave exposes a dedicated **Streamable HTTP** Model Context Protocol
resource server at `/mcp`. It is a separate ASGI process from the product REST
API, but it reuses the same PostgreSQL source of truth, Keycloak/Keyverse issuer,
`post_read` permission, account affiliations, ABAC visibility rule, Event-Lineage
retrieval, content normalization, and contextual-orchestrator reason-and-cite
client.

## Tool contract

`global_ask(question, verify_external=false)` is read-only and idempotent with
respect to LineageWeave state. The default call is closed-world: it uses only
caller-authorized LineageWeave evidence. Because a caller can explicitly opt
into public-web corroboration, the MCP tool truthfully advertises
`open_world_hint=true`.

The response separates two evidence planes.

### Internal LineageWeave answer

- `answer_text`
- the selected `anchor_post_id`
- `source_post_ids` for every bounded source passed to the reasoner
- `cited_post_ids` and `cited_posts`

The tool never promotes an inferred answer to an authoritative fact. Citation
IDs not present in the authorized internal source bundle are discarded; if no
authorized citation remains, the call fails instead of returning unsupported
prose. No Global Ask row is written merely because an MCP client asked a
question.

The reason-and-cite call uses contextual-orchestrator's supported
`mode="conduct"` contract with high reasoning effort. It does not use the
rejected legacy `verify` mode and never falls back to a direct model provider.
The downstream call is bounded to 300 seconds so verified orchestration is not
prematurely cut off while remaining finite.

### Explicit external corroboration

When and only when the caller sends `verify_external=true`, the tool sends a
bounded form of the caller's question to the configured self-hosted Searxng
search lane. It never uses the private internal answer body as a search query.
Retrieved public results are bounded, deduplicated, restricted to public
HTTP(S) URLs without credentials, and passed with the internal answer to
contextual-orchestrator as one explicitly untrusted JSON document.

The output fields are separate from LineageWeave authority:

- `external_verification_status`: `supported`, `refuted`,
  `insufficient_evidence`, `unavailable`, or `not_requested`
- `external_evidence_urls`
- `external_verification_rationale`

`not_requested`, `unavailable`, and `insufficient_evidence` are unresolved
states, not support. `supported` or `refuted` requires at least one valid cited
external URL; otherwise the status is downgraded to `insufficient_evidence`.
External evidence does not become a `source_post`, does not satisfy RBAC or
ABAC, and cannot upgrade an inference into an authoritative audit or lineage
fact.

## Authentication and authorization

The MCP endpoint is an OAuth protected resource:

1. the bearer JWT signature is verified against issuer JWKS;
2. `iss`, expiry, mandatory exact `kid`, and the configured MCP `audience` are
   verified;
3. malformed JWKS structures fail closed;
4. optional `MCP_REQUIRED_SCOPES` are enforced by the MCP SDK;
5. the token `sub` must resolve to a provisioned `user_account`;
6. the account must have `post_read`;
7. every candidate and every lineage-expanded internal source is checked
   against the existing public-or-affiliated ABAC rule.

The inbound bearer token is never forwarded to contextual-orchestrator,
Searxng, or any other downstream service. Provider credentials remain service
credentials.

### Required deployment settings

```text
MCP_RESOURCE_URL=https://lineage.example.com/mcp
MCP_AUDIENCE=https://lineage.example.com/mcp
MCP_ALLOWED_HOSTS=lineage.example.com
MCP_ALLOWED_ORIGINS=https://buyer.example.com
MCP_REQUIRED_SCOPES=lineageweave:ask
MCP_MAX_REQUEST_BYTES=65536
```

The identity provider must issue access tokens whose `aud` includes the exact
`MCP_AUDIENCE`. The scope is optional at the product default because database
RBAC is mandatory regardless; production deployments should provision and
require `lineageweave:ask`.

DNS-rebinding protection is enabled. Do not disable it to make a deployment
work; add only the real public hostname and exact browser origins. Each
`MCP_ALLOWED_ORIGINS` entry must be an HTTP(S) origin with no wildcard,
credentials, path, query, or fragment. `*`, `null`, malformed entries, and
non-origin URLs prevent process startup.

## Browser admission boundary

A browser sends an unauthenticated CORS preflight before a cross-origin POST
that uses `Authorization`, JSON, and MCP headers. LineageWeave handles that
preflight **after exact Host/Origin transport validation and before OAuth**.
The preflight never verifies a token, resolves an account, opens Global Ask, or
consumes a tool invocation quota.

The browser contract is deliberately narrow:

```text
Allowed origins: exact MCP_ALLOWED_ORIGINS entries only
Allowed methods: GET, POST, DELETE
Allowed request headers:
  Accept
  Authorization
  Content-Type
  Last-Event-ID
  MCP-Protocol-Version
  Mcp-Session-Id
Exposed response headers:
  MCP-Protocol-Version
  Mcp-Session-Id
  WWW-Authenticate
Credentials/cookies: disabled
Preflight cache: 600 seconds
```

`WWW-Authenticate` is exposed so an allowed browser client can read the OAuth
protected-resource metadata challenge. It does not expose a credential.
LineageWeave never reflects an arbitrary Origin and never accepts `*`. Prefix,
suffix, `null`, and unrelated Origins fail with HTTP `403`. Origin-sensitive
responses include `Vary: Origin`. Non-browser clients may omit `Origin`; they
continue directly to the normal OAuth challenge or authenticated MCP request.

Example preflight:

```http
OPTIONS /mcp HTTP/1.1
Host: lineage.example.com
Origin: https://buyer.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: authorization, content-type, mcp-protocol-version, mcp-session-id
```

## Request-byte admission

For every MCP POST, the resource server validates and counts the request body
before OAuth or MCP SDK JSON decoding. The default maximum is 65,536 bytes.
`MCP_MAX_REQUEST_BYTES` may be set from 8,192 through 1,048,576 bytes; a value
outside that range or a malformed integer prevents process startup.

`Content-Length` enables an early rejection but is not trusted as the only
boundary. Bodies without it remain supported and are counted chunk by chunk.
The endpoint rejects:

- a negative, nondecimal, non-ASCII, or duplicate `Content-Length`;
- `Content-Length` together with `Transfer-Encoding`;
- a declared length larger than the configured maximum;
- an actual streamed body larger than the maximum;
- declared and received byte counts that differ;
- a disconnect or malformed ASGI body message during admission.

An admitted body is replayed byte-for-byte once to the MCP SDK. Errors are
bounded JSON, do not echo request content, and include `Cache-Control: no-store`:

| HTTP | `error_code` | Operator/client action |
|---:|---|---|
| 400 | `mcp_invalid_content_length` | Remove ambiguous or malformed framing headers. |
| 400 | `mcp_content_length_mismatch` | Correct the sender or intermediary framing. |
| 400 | `mcp_request_disconnected` | Retry only after the transport is stable. |
| 400 | `mcp_invalid_request_body` | Send a valid ASGI/HTTP request body. |
| 413 | `mcp_request_too_large` | Reduce the MCP request; do not raise the limit without capacity review. |

A reverse proxy must still implement HTTP framing correctly. Application-level
admission is defense in depth and does not make an unsafe intermediary safe.

External verification additionally requires all three service settings:

```text
SEARXNG_BASE_URL=https://search.internal.example
ORCHESTRATOR_BASE_URL=https://orchestrator.internal.example
ORCHESTRATOR_API_KEY=<service credential>
```

An absent channel returns `unavailable` after explicit opt-in; it never
silently substitutes a third-party search API or direct model provider.

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

The Codex timeout is set slightly above LineageWeave's 300-second primary-answer
bound so the server, not the client, returns the actionable failure. A normal
call omits `verify_external` or sets it to `false`. A caller should set it to
`true` only after determining that transmitting the question to the configured
public-search lane is permitted for that task.

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
not accept the REST frontend audience as a substitute. Compose passes
`MCP_MAX_REQUEST_BYTES` into the dedicated MCP process rather than the product
REST API.

## Failure behavior

- unsafe configured browser Origin: process startup fails
- untrusted Host: HTTP `421` before authentication
- invalid present Origin: HTTP `403` before authentication
- invalid browser preflight: HTTP `400` or `403`, no bearer challenge
- oversized or ambiguously framed POST: HTTP `400` or `413` before authentication
- no bearer or invalid bearer: HTTP `401`, with browser-readable OAuth metadata for an allowed Origin
- valid bearer without a required OAuth scope: HTTP `403`
- unprovisioned subject or missing `post_read`: tool error, no evidence returned
- no matching authorized evidence: tool error, no unrelated recent-post fallback
- contextual-orchestrator unavailable, malformed, or uncited: tool error, no invented answer
- unknown internal citation ID: omitted; all-unknown citations fail the call
- external verification not requested: `not_requested`, no search call
- external search/judge unavailable: primary answer remains, external status `unavailable`
- externally supported/refuted without a valid cited public URL: `insufficient_evidence`

## Operational checks

A release must exercise the MCP SDK client against the in-process server, assert
tool annotations and structured output, verify pre-auth Host, Origin, CORS,
request-byte, OAuth-discovery, and unauthenticated HTTP behavior, and run the
same auth, ABAC, source-boundary, citation, contextual-orchestrator mode,
explicit-consent, untrusted-input, URL-safety, and external-evidence regressions
in the normal test suite. `uv.lock` remains authoritative for the MCP SDK
version.

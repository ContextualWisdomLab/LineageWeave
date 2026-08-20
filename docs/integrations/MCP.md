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
- `timeline`: chronological source entries with `post_id`, `post_title`,
  `occurred_at`, and `lineage_relation`
- `content_blocks`: bounded prose and cited raster-image metadata

The tool never promotes an inferred answer to an authoritative fact. Citation
IDs not present in the authorized internal source bundle are discarded; if no
authorized citation remains, the call fails instead of returning unsupported
prose. No Global Ask row is written merely because an MCP client asked a
question.

The timeline is calculated from the same authorized source bundle used by the
answer. It is ordered by each post's persisted `created_at` and distinguishes
the anchor from direct Event-Lineage and indirect Knowledge-Graph context. A
successful answer is therefore actionable as a sequence, not just an unordered
citation list.

Inline images are emitted only for cited posts, limited to three images and four
MiB total, with PNG, JPEG, WebP, and GIF accepted. A citation is not a media
authorization lease: immediately before any raster bytes are serialized,
LineageWeave queries the database again for the requesting account's live
`post_read` grant and current corporate affiliations. If either was revoked
since source selection, affected images are omitted. The answer remains bounded
and never substitutes a remote image URL or stale cached media.

The reason-and-cite call uses contextual-orchestrator's `mode="auto"` and
`reasoning_effort="auto"` contract. The gateway chooses the model, provider
protocol, and multi-agent workflow, including Responses-only providers; this
client never sends a model name or falls back to a direct provider. It sends a
strict `json_schema` response contract and post-scoped `session_id` plus
non-secret post/author/PU/corp metadata. The downstream call is bounded to 300
seconds while remaining finite.

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
   against the existing public-or-affiliated ABAC rule;
8. cited media is authorized again from live database permission and affiliation
   state immediately before byte disclosure.

The inbound bearer token is never forwarded to contextual-orchestrator,
Searxng, or any other downstream service. Provider credentials remain service
credentials.

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

External verification additionally requires all three service settings:

```text
SEARXNG_BASE_URL=https://search.internal.example
LLM_GATEWAY_URL=https://orchestrator.internal.example
LLM_GATEWAY_API_KEY=<service credential>
```

The backend reads process environment first and then `~/.env` for these
gateway settings. `LLM_GATEWAY_API_URL` and the older `ORCHESTRATOR_*` names
remain compatibility aliases. Never copy, log, commit, or ship the secret.

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

Start the required services with the one-shot audience reconciler included:

```bash
docker compose up --build postgres keycloak keycloak_mcp_audience mcp
```

The default endpoint is `http://localhost:18001/mcp`. A fresh demo database
receives the audience through the rendered realm import template. Keycloak
startup import deliberately skips a realm that already exists, so the separate
`keycloak_mcp_audience` service then authenticates to the local Admin REST API
and reconciles **only** the `lineageweave-mcp-audience` mapper on the
`lineageweave-frontend` client. The MCP service waits for that one-shot job to
finish successfully.

Consequently, changing the local published port is non-destructive:

```bash
MCP_PORT=19001 docker compose up --build keycloak keycloak_mcp_audience mcp
```

The reconciler changes the existing mapper from
`http://localhost:18001/mcp` to `http://localhost:19001/mcp` without replacing
the realm, users, roles, sessions, or unrelated client configuration. Re-running
it with the same audience is idempotent. Duplicate same-name mappers, a
conflicting mapper type, unsafe audience URLs, missing target clients, or
unavailable administration fail closed and prevent MCP startup.

The Compose demo uses its bootstrap administrator for this bounded local
reconciliation. A production deployment should provision a narrower Keycloak
service account or external identity-management reconciler with only the client
and protocol-mapper permissions it needs. A different public host still
requires a corresponding exact IdP audience and environment change; do not
accept the REST frontend audience as a substitute.

## Failure behavior

- untrusted Host: HTTP `421` before authentication
- no bearer or invalid bearer: HTTP `401`
- valid bearer without a required OAuth scope: HTTP `403`
- unprovisioned subject or missing `post_read`: tool error, no evidence returned
- no matching authorized evidence: tool error, no unrelated recent-post fallback
- permission or affiliation revoked before media read: affected image blocks omitted
- contextual-orchestrator unavailable, malformed, or uncited: tool error, no invented answer
- unknown internal citation ID: omitted; all-unknown citations fail the call
- external verification not requested: `not_requested`, no search call
- external search/judge unavailable: primary answer remains, external status `unavailable`
- externally supported/refuted without a valid cited public URL: `insufficient_evidence`
- persistent Keycloak mapper cannot be reconciled: MCP container does not start

## Operational checks

A release must exercise the MCP SDK client against the in-process server, assert
tool annotations and structured output, verify Host and unauthenticated HTTP
rejection, and run the same auth, ABAC, source-boundary, citation,
contextual-orchestrator mode, explicit-consent, untrusted-input, URL-safety,
external-evidence, live-media-authorization, and persistent-audience
reconciliation regressions in the normal test suite. `uv.lock` remains
authoritative for the MCP SDK version.

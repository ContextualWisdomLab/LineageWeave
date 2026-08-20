# ADR 0031: Authenticated MCP Global Ask

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Codex and other agent clients need a supported way to ask questions over
LineageWeave evidence. Giving an agent direct SQL, forwarding a UI token to an
LLM, exposing a shared-secret endpoint, or copying source posts into a second
MCP database would break the existing identity, ABAC, provenance, and inference
boundaries.

LineageWeave already owns source-post visibility, Event-Lineage reconstruction,
normalized evidence assembly, and contextual-orchestrator-based source-only
answers. The MCP surface should adapt those responsibilities, not reimplement
or bypass them.

The current contextual-orchestrator HTTP contract accepts `auto`, `route`, and
`conduct`; it rejects the older LineageWeave `verify` request. This product
uses `auto`: contextual-orchestrator owns model discovery, provider protocol
(including Responses-only providers), multi-agent synthesis, and reasoning
allocation. The caller must not select a model.

Some buyer questions concern Knowledge Graph, ontology, or semantic claims that
benefit from independent public corroboration. That lane must be explicit and
must not turn public snippets into internal authority or silently export a
private answer as a search query.

## Decision

1. Run MCP as a dedicated ASGI process using MCP Python SDK 2.0.0 and
   Streamable HTTP.
2. Treat the endpoint as an OAuth protected resource. Validate issuer,
   signature, expiry, mandatory exact JWKS `kid`, and an exact MCP resource
   audience. Refresh JWKS once on an unknown key to tolerate issuer rotation;
   reject malformed JWKS structures as service unavailable.
3. Resolve the JWT subject through the existing `user_account`, role,
   permission, and affiliation tables. Never authorize from `corp_code` or
   `pu_code` token claims.
4. Expose one bounded, structured, read-only and idempotent tool:
   `global_ask(question, verify_external=false)`.
5. Keep the default invocation closed-world. Search only caller-visible posts,
   refuse an unrelated fallback when a concrete search term has no match, then
   expand the chosen anchor through the existing Event-Lineage/Knowledge-Graph
   source gatherer with ABAC re-checking.
6. Limit retrieval terms, candidate rows, source count, and source-body bytes
   before invoking contextual-orchestrator.
7. Use contextual-orchestrator `mode="auto"`, `reasoning_effort="auto"`, and a
   finite 300-second downstream timeout. Use a strict `json_schema` response
   contract and `system` instructions on Chat Completions; the orchestrator
   translates them to `developer` for Responses providers. Never call a direct
   provider or the rejected legacy `verify` mode.
8. Give every request about one post the stable session id
   `lineageweave:post:{post_id}` and non-secret metadata for the post,
   author, PU, corp code, and requesting account. Drop citations outside the
   authorized source bundle and reject an answer when no authorized citation
   remains. Do not persist a Global Ask exchange as a side effect.
9. Permit open-web corroboration only when the caller explicitly sends
   `verify_external=true`. Search using a bounded form of the caller's question,
   never the private internal answer body.
10. Treat the question, answer, public titles, URLs, and snippets as one
    explicitly untrusted JSON document for the external judge. Restrict returned
    evidence to bounded public HTTP(S) URLs without credentials or local/private
    literal addresses.
11. Keep external status, rationale, and cited URLs separate from internal
    source authority. `supported` or `refuted` requires at least one valid cited
    external URL; otherwise return `insufficient_evidence`.
12. Advertise `open_world_hint=true` because the tool has an explicit optional
    external lane even though the default remains closed-world.
13. Keep the bearer token inside the resource server. Downstream services use
    their own credentials.
14. Enable Host and Origin validation for DNS-rebinding protection.
15. Resolve the contextual-orchestrator URL/key from process environment first,
    then the user's `~/.env` using `LLM_GATEWAY_URL` (or the compatibility
    alias `LLM_GATEWAY_API_URL`) and `LLM_GATEWAY_API_KEY`. Never copy, log, or
    commit the secret; `ORCHESTRATOR_BASE_URL` and `ORCHESTRATOR_API_KEY` are
    compatibility fallbacks only.

## Consequences

- Codex can use a bearer token immediately and OAuth login after the identity
  provider provisions compatible client registration.
- The MCP process can scale and fail independently from the web UI while sharing
  the same authoritative database.
- Answers remain inferred, evidence-grounded results; they do not become
  authoritative audit events or lineage facts.
- A configured contextual-orchestrator with a working `auto` runtime remains
  required for a live internal answer. The server fails closed rather than
  substituting a local model, direct provider, or canned prose.
- Public corroboration is available without becoming an authorization or truth
  source. Callers retain the decision to cross the search boundary for each
  invocation.
- Deployments must configure an audience for the exact public MCP resource URL.
- Codex deployments should set a tool timeout slightly above 300 seconds so the
  server returns the bounded downstream failure instead of a client timeout.

## Rejected alternatives

- **Unauthenticated local-only MCP:** cannot support enterprise remote clients.
- **Static MCP API key:** creates a second identity and revocation system.
- **Direct SQL tool:** leaks schema and bypasses RBAC/ABAC application policy.
- **Proxy the REST endpoint:** couples MCP availability and schemas to the UI
  API and encourages token forwarding.
- **Store a second MCP search index containing full posts:** duplicates
  restricted evidence and creates deletion/authorization drift.
- **Legacy `mode="verify"`:** rejected by the current orchestrator HTTP API.
- **Direct provider fallback:** bypasses contextual-orchestrator governance,
  verification, model discovery, and service credentials.
- **Automatic web verification:** leaks caller questions without explicit task
  consent and misrepresents a normally closed-world evidence tool.
- **Search the internal answer text:** can disclose private evidence-derived
  content to the public-search boundary and invites prompt/search injection.

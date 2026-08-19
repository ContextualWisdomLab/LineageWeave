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

## Decision

1. Run MCP as a dedicated ASGI process using MCP Python SDK 2.0.0 and
   Streamable HTTP.
2. Treat the endpoint as an OAuth protected resource. Validate issuer,
   signature, expiry, mandatory exact JWKS `kid`, and an exact MCP resource
   audience. Refresh JWKS once on an unknown key to tolerate issuer rotation.
3. Resolve the JWT subject through the existing `user_account`, role,
   permission, and affiliation tables. Never authorize from `corp_code` or
   `pu_code` token claims.
4. Expose one bounded, structured, read-only tool: `global_ask`.
5. Search only caller-visible posts, refuse an unrelated fallback when a
   concrete search term has no match, then expand the chosen anchor through
   the existing Event-Lineage/Knowledge-Graph source gatherer with ABAC
   re-checking.
6. Limit retrieval terms, candidate rows, source count, and source-body bytes
   before invoking contextual-orchestrator.
7. Return source and citation identities. Drop citations outside the authorized
   source bundle. Do not persist a Global Ask exchange as a side effect.
8. Keep the bearer token inside the resource server. Downstream services use
   their own credentials.
9. Enable Host and Origin validation for DNS-rebinding protection.

## Consequences

- Codex can use a bearer token immediately and OAuth login after the identity
  provider provisions compatible client registration.
- The MCP process can scale and fail independently from the web UI while sharing
  the same authoritative database.
- Answers remain inferred, evidence-grounded results; they do not become
  authoritative audit events or lineage facts.
- A configured contextual-orchestrator remains required for a live answer. The
  server fails closed rather than substituting a local model or canned prose.
- Deployments must configure an audience for the exact public MCP resource URL.

## Rejected alternatives

- **Unauthenticated local-only MCP:** cannot support enterprise remote clients.
- **Static MCP API key:** creates a second identity and revocation system.
- **Direct SQL tool:** leaks schema and bypasses RBAC/ABAC application policy.
- **Proxy the REST endpoint:** couples MCP availability and schemas to the UI
  API and encourages token forwarding.
- **Store a second MCP search index containing full posts:** duplicates
  restricted evidence and creates deletion/authorization drift.
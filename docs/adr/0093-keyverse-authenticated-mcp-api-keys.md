# ADR 0093: Keyverse-authenticated API keys for MCP clients

## Status

Accepted for the Buyer product boundary.

## Context

LineageWeave must open with its own login screen. A first visit must not
silently navigate the browser to the Keyverse login page, and a login from a
deep link such as `/?post=<id>` must return to that same link. OIDC remains
the trust boundary: LineageWeave is the relying party and Keyverse is the
identity provider. The browser sends only the OIDC authorization request,
redirect URI, and opaque state to Keyverse; it never sends a password or a
provider credential from this repository.

MCP clients commonly need a bearer credential even when they cannot perform a
browser OIDC flow. This repository currently has no MCP protocol endpoint,
and Keyverse has no public API-key-management contract available to this
project. Inventing a Keyverse API or silently reusing the internal
orchestrator credential would create an unsafe trust-boundary shortcut.

## Decision

1. The LineageWeave entry point renders a local login screen first. The user
   explicitly starts the Keyverse OIDC authorization flow. The requested
   same-origin deep link is carried in OIDC state and session storage, and the
   callback restores it only after same-origin validation.
2. The authenticated `user_account` resolved from the Keyverse OIDC subject
   may create, list, and revoke its own LineageWeave MCP keys through
   `/api/api-keys`. `post_read` is required for issuance because the only
   initial scope is `mcp:read`.
3. API key material is generated with the standard library, returned once at
   creation, and stored only as a SHA-256 digest. Key name, scope, lifecycle,
   and audit events are separate tables; no secret, provider token, or JSON
   blob is stored in the registry.
4. MCP keys are not accepted as general LineageWeave bearer tokens. The
   narrow `resolve_mcp_api_key` seam is reserved for the eventual MCP
   transport, where the scope must be checked before an MCP operation.
   Until that server contract exists, no fake `/mcp` route is added.

## Consequences

- Users get a stable LineageWeave login landing page and deep-link return.
- An MCP client can receive a narrowly scoped, revocable credential without
  needing an OIDC browser flow.
- The raw key cannot be recovered after issuance; a lost key must be revoked
  and replaced.
- Keyverse account deprovisioning must remove or disable the corresponding
  `user_account`; the database remains the authorization authority for the
  product, as established by ADR 0028.
- A future MCP server must be implemented in the repository that owns its MCP
  protocol contract and must call the narrow resolver; it must not broaden
  `get_current_account` to accept these keys.

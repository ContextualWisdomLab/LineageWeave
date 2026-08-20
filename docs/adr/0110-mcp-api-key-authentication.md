# ADR 0110: Authenticate MCP with LineageWeave-managed API keys

- Status: Accepted
- Date: 2026-08-21
- Depends on: ADR 0103 and PR #333 (`mcp_api_key` lifecycle)

## Context

LineageWeave exposes an authenticated MCP server. ADR 0103 establishes that
Keyverse is the identity boundary while LineageWeave owns the normalized,
owner-scoped application key resource. A key that can be created in the
LineageWeave settings screen but cannot authenticate the MCP server is not a
usable buyer capability.

## Decision

The MCP resource server accepts two bearer forms:

1. Keyverse/Keycloak OIDC JWTs continue through the existing signature,
   issuer, audience, expiry, and subject validation.
2. A LineageWeave application key with the `lw_mcp_` prefix is hashed with
   SHA-256 and looked up in `mcp_api_key`. Only a non-revoked, non-expired key
   joined to a provisioned `user_account` yields an MCP `AccessToken`.

The API key never becomes a new identity. Its `user_account.external_subject_id`
is the MCP subject, so the existing account resolver and ABAC/RBAC checks remain
the authorization authority. The raw key is never stored or logged.

The MCP lifespan binds its existing PostgreSQL pool to the verifier and clears
that binding during shutdown. If the key-management migration is not deployed,
API-key authentication is unavailable while OIDC authentication remains intact;
the verifier does not turn a schema deployment race into a server-wide outage.

## Consequences

- Settings-created keys are directly usable by MCP clients after PR #333 and
  this authentication change are deployed together.
- Revocation and expiry take effect at the database lookup boundary.
- Key issuance remains LineageWeave UI/API behavior; Keyverse remains the
  identity and account-provisioning authority.
- A future Keyverse-native application-key resource can replace the lookup
  without changing the MCP tool contract, but no second credential source is
  introduced now.

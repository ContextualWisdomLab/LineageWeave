# ADR 0103: Keyverse-authenticated MCP API keys

- Status: Accepted
- Date: 2026-08-21
- Scope: LineageWeave buyer UI and MCP adapter boundary

## Decision

LineageWeave begins with its own login screen. Keyverse is the OIDC issuer and
account authority after the buyer chooses **Log in**; LineageWeave resolves the
verified subject to its normalized `user_account` row.

LineageWeave owns application-scoped MCP API-key lifecycle because the current
Keyverse contract provides identity, OIDC claims, and operator-controlled
identity administration, not a user-scoped application-key resource. The
LineageWeave API therefore stores only a SHA-256 digest, the constant
non-secret `lw_mcp_` family prefix,
label, timestamps, and the owning `user_account_id`. The raw random key is
returned once on creation and is never returned by list, revoke, logs, or
runtime configuration.

Every list/create/revoke operation is scoped to the authenticated account. A
foreign key is indistinguishable from a missing key. Keyverse operator tokens
and Keycloak admin credentials never cross into the browser or MCP client.

## Consequences

- The buyer can create, copy once, inspect metadata, and revoke keys from the
  authenticated LineageWeave Settings destination.
- A future MCP transport resolves a presented key through
  `resolve_mcp_api_key()` and then applies the same account/resource ABAC rules;
  the key is not an authorization bypass.
- Central cross-application key lifecycle is intentionally not invented until
  Keyverse publishes a user-scoped API-key contract. That future contract can
  replace the resource owner without changing the buyer-facing boundary.

## Rejected alternatives

- Passing the Keyverse operator bearer token to the browser would grant a
  coarse identity-administration capability and violate ADR 0008.
- Storing raw API keys would turn a database read into an immediate credential
  compromise.
- A `user_account + post_id` session or key table would violate the existing
  normalized identity/resource boundary; MCP keys are independent entities.

# ADR 0028: Use Keyverse as a real OIDC provider in production

## Status

Accepted for version 2.10.0.

## Context

LineageWeave must use real user accounts for login, while corporation and PU
attributes remain authorization data. The local Compose stack needs a portable
development identity provider, but a Keycloak container is not Keyverse and
must not be presented as one.

## Decision

1. Production sets `KEYVERSE_ISSUER` and `KEYVERSE_CLIENT_ID` to the actual
   Keyverse OIDC client configuration.
2. The backend uses OIDC discovery from that issuer and fetches the returned
   `jwks_uri` for RS256 verification. `KEYVERSE_DISCOVERY_URI` and
   `KEYVERSE_JWKS_URI` are explicit overrides for deployments where discovery
   is proxied.
3. The verified `sub` is resolved to a provisioned `user_account`; the database
   remains authoritative for affiliations and permissions. ADR 0156 further
   requires the production Keyverse `org`, `workspace`, and `role` claims to
   select one matching local scope before either authority is used.
4. Compose uses its existing local Keycloak realm only when no Keyverse issuer
   is configured. It does not add a Keyverse-shaped identity implementation.

## Consequences

- A real Keyverse tenant can be used without changing application code.
- A deployment must provision the Keyverse client, redirect URI, and matching
  `user_account` rows before login is usable.
- Local OIDC smoke tests continue to prove cryptographic behavior against the
  synthetic Keycloak realm, while production validation must run against the
  configured Keyverse discovery document.

## Security boundary

Non-HTTP(S) discovery and JWKS URLs are rejected by the shared HTTP client.
No bearer token, client secret, or Keyverse credential belongs in this
repository or in the browser bundle.

# ADR 0028: Use Keyverse as a real OIDC provider in production

## Status

Accepted for version 2.10.0.

The production Keyverse decision remains Accepted. The local development/test
hardening amendment below is Proposed in #1120 until its executable contracts,
rendered browser acceptance, and exact-head validation are complete.

## Context

LineageWeave must use real user accounts for login, while corporation and PU
attributes remain authorization data. The local Compose stack needs a portable
development identity provider, but a Keycloak container is not Keyverse and
must not be presented as one.

The original local fixture also enabled the Resource Owner Password Credentials
grant on the public browser client and reused that shortcut in smoke, backend
integration, seed, and load-test actors. That topology blurred three different
security claims: browser authentication, machine authentication, and local
fixture/bootstrap administration. RFC 9700 section 2.4 prohibits the Resource
Owner Password Credentials grant, and browser applications require a redirect
flow rather than a password-token shortcut. A machine token likewise must not
be presented as evidence that the rendered browser flow works.

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
4. Compose uses its local Keycloak realm only when no Keyverse issuer is
   configured. It does not add a Keyverse-shaped identity implementation.
5. The local public browser client uses Authorization Code with mandatory PKCE
   S256. Direct access/password grants and service accounts are disabled on
   that public client. Rendered browser acceptance must exercise the actual
   authorization endpoint, callback/session restoration, return URL, and a
   protected product request; token/JWKS probes cannot substitute for it.
6. Repository-owned non-browser smoke and load actors use a separate
   confidential, synthetic service-account client with the OAuth 2.0 Client
   Credentials grant. Its secret is runtime-only, its resource audiences are
   explicit, and its `sub` must be provisioned into the same normalized local
   authorization tables before a buyer-path test can claim RBAC/ABAC evidence.
7. Product integration tests that prove authorization between distinct people
   or accounts preserve distinct subjects. They must not collapse an analyst
   and an administrator into one service-account identity merely to remove a
   password grant. Machine setup evidence and end-user authorization evidence
   remain different contracts.
8. Local seed/bootstrap work uses no password grant. If the repository-owned
   realm fixture already contains deterministic synthetic subject identifiers,
   seed code consumes that fixture truth rather than adding an administrative
   network login solely to rediscover the same identifiers. Any Admin REST
   operation that remains necessary must use its own purpose-bound confidential
   bootstrap actor with only the required administrative roles; it must not
   expand the smoke/load client's privilege.
9. Synthetic credentials may be represented by environment placeholders in the
   local realm fixture and Compose wiring. Real bearer tokens, client secrets,
   Keyverse credentials, and production identity data remain runtime-only and
   must not be committed, logged, or bundled into the browser.

## Ordering and invariants

The migration is fail-closed and ordered: remove password-grant consumers and
provision their replacement subjects first; then disable direct grants on the
public client; then prove the focused/full repository and rendered browser
contracts on the same exact head. A realm-only hardening that breaks existing
test/buyer actors is not an acceptable intermediate state.

The current #1120 local fixture now performs the authorization half of that
ordering explicitly. After `scripts/seed_demo_data.py` creates Demo Corp,
process units and access roles, `scripts/provision_local_service_accounts.py`
maps the realm-declared automation subject
`33333333-3333-4333-8333-333333333333` to `DEMO-PU-A` + `viewer` and the
distinct admin-test subject `44444444-4444-4444-8444-444444444444` to
`DEMO-PU-HQ` + `admin`. The provisioner talks only to PostgreSQL, replaces only
those deterministic fixture actors' affiliation/role rows in one transaction,
and never authenticates to Keycloak. This closes the normalized machine/admin
authorization prerequisite at source level without claiming hosted acceptance.
The public client's direct grants remain enabled until the remaining backend and
seed password-grant consumers have migrated, so this intermediate state does
not break their current evidence paths.

Keycloak startup realm import is a disposable local-fixture mechanism. The
repository source remains `docker/keycloak/realm-export.json`; the image may
install it under Keycloak's realm-name import filename. Because Keycloak skips
startup import when a realm already exists, a stale persistent local realm is
not evidence for the current fixture and must be recreated intentionally when
fixture identity changes.

## Consequences

- A real Keyverse tenant can be used without changing application code.
- A deployment must provision the Keyverse client, redirect URI, and matching
  `user_account` rows before login is usable.
- Local machine smoke tests prove signature/issuer/audience/client behavior only;
  they do not prove browser login, SSO, MFA, callback state, or return-URL
  restoration.
- Local performance and integration actors cannot obtain product authorization
  merely by possessing a valid machine token; their exact subject must also be
  provisioned in LineageWeave's normalized authorization state.
- The local demo fixture can use deterministic synthetic identities to remove
  unnecessary administrative discovery traffic, but those identifiers remain
  test data and are never production account truth.

## Security boundary

Non-HTTP(S) discovery and JWKS URLs are rejected by the shared HTTP client.
No bearer token, client secret, or Keyverse credential belongs in this
repository or in the browser bundle. LineageWeave does not copy Keyverse or
Keycloak provider/domain truth; it owns only its local fixture, consumer
configuration, normalized authorization binding, and product acceptance.

## References

Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). *Best current
practice for OAuth 2.0 security* (RFC 9700). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9700

OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set
2*. https://openid.net/specs/openid-connect-core-1_0.html

Keycloak. (2026). *Server Administration Guide: Using a service account*.
https://www.keycloak.org/docs/latest/server_admin/

Keycloak. (2026). *Importing and exporting realms*.
https://www.keycloak.org/server/importExport
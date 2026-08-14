---
id: "0003"
title: "Authenticate through Keyverse authorization code with PKCE"
status: accepted
proposed_date: 2026-08-13
accepted_date: 2026-08-13
deciders:
  - "LineageWeave delivery owner"
consulted:
  - "product request"
  - "Keyverse relying-party contract"
informed:
  - "Keyverse, database, and deployment operators"
related:
  - path: "docs/planning/adrs/0001-lineageweave-runtime-and-governance.md"
    relation: "influenced-by"
    note: "Refines the Keyverse boundary selected for the direct PostgreSQL product."
  - path: "docs/planning/adrs/0002-verified-inline-image-inspection.md"
    relation: "influenced-by"
    note: "Uses the same verified TLS and document authorization boundary."
affected_components:
  - "lineageweave_server.py"
  - "lineageweave.py"
  - "compose/http_standin.py"
  - "compose.yaml"
  - "web/src/App.jsx"
  - "web/src/styles.css"
  - "web/e2e/lineageweave.mjs"
  - "tests/test_http_contract.py"
  - "tests/test_keyverse_server_contract.py"
  - "tests/test_prototype_surfaces.py"
  - "tests/test_worker_contract.py"
  - "tests/test_identity_boundary_lock.py"
asr_triggers:
  - kind: security
    evidence: "The browser must not collect or relay account passwords or choose tenant attributes."
    note: "The relying party uses authorization code with PKCE and server-side token introspection."
  - kind: compliance
    evidence: "Tenant and role claims gate all protected document, evidence, asset, and graph data."
    note: "Issuer, audience, client, activity, expiry, and mapped claims are validated before authorization."
  - kind: availability
    evidence: "Identity endpoint or trust failure must not create a permissive local session."
    note: "Configuration and discovery fail closed; sessions expire no later than the access token."
  - kind: maintainability
    evidence: "A custom password-session adapter diverges from the supported Keyverse relying-party contract."
    note: "OIDC discovery and one validated claim projection keep the boundary small and reviewable."
  - kind: evolvability
    evidence: "The product must accept browser sessions and API bearer tokens without duplicating authorization logic."
    note: "Both paths converge on the same Keyverse introspection and actor projection."
success_criteria:
  - metric: "OIDC request integrity"
    target: "Every browser login starts an authorization-code request with S256 PKCE and a bounded, matching state value."
    measurement_window: "each login attempt"
    source: "begin_keyverse_login and complete_keyverse_login"
  - metric: "claim verification"
    target: "Only active tokens with exact issuer, audience, client identifier, future expiry, subject, organization, workspace, and mapped role create an actor."
    measurement_window: "each callback or bearer request"
    source: "_actor_from_keyverse_access_token"
  - metric: "browser credential boundary"
    target: "The product has no account or password input, asks only for an email address before redirect, and rejects POST /api/session."
    measurement_window: "each release"
    source: "web/src/App.jsx and LineageHandler.do_POST"
  - metric: "email-first redirect guard"
    target: "A missing or malformed email never starts an authorization request; a valid email is passed only as the standard OIDC login_hint."
    measurement_window: "each login attempt"
    source: "LineageHandler.do_GET, begin_keyverse_login, and React login form"
  - metric: "session lifetime"
    target: "A local opaque session never outlives its validated access token."
    measurement_window: "each successful callback"
    source: "complete_keyverse_login"
  - metric: "worker identity exclusion"
    target: "The Compose worker returns 404 for OIDC discovery, authorization, token, and introspection routes; it contains no OIDC issuer configuration, local issuer import, or local issuer build copy."
    measurement_window: "each release"
    source: "compose/http_standin.py, compose/Dockerfile, compose.yaml, tests/test_worker_contract.py, and tests/test_identity_boundary_lock.py"
effort: M
---

# ADR-0003: Authenticate through Keyverse authorization code with PKCE

## Context

> Product requirement: a real Keyverse account authenticates the user; legal-company and PU values are IdP attributes, never browser login fields.

> The Keyverse relying-party contract uses OpenID Connect authorization code, PKCE S256, discovery, and server-side validation of issuer, audience, expiry, and tenant-role claims.

> The product must fail closed when a Keyverse client is not provisioned; an explicit development actor is the only local exception. A Compose model proxy is never a substitute identity provider.

The initial adapter shape accepted a browser account identifier and credential before it could obtain tenant attributes. That is neither a Keyverse relying-party flow nor a safe business boundary: it places a password contract in the product, makes the application responsible for an IdP concern, and creates a second session semantic to audit.

The product needs ordinary browser SSO, secure API access, and one actor projection for ABAC/RBAC. Keyverse's approved claim semantics provide `sub`, `org`, `workspace`, and `role`; LineageWeave maps them to `account_id`, `corp_code`, `pu_code`, and product roles after the token is validated.

## Decision Drivers

- Use actual IdP authentication without collecting a password in LineageWeave.
- Bind every tenant and role decision to claims validated for this relying party.
- Preserve verified transport, bounded server state, and a predictable operational failure mode.
- Keep browser sessions and API bearer access on one authorization projection.
- Retain an explicit, isolated development path without weakening production defaults.

## Considered Options

| Option | Credential and claim safety | Operational behavior | Maintenance | Decision |
| --- | --- | --- | --- | --- |
| Browser password form posted to a product session adapter | Creates a parallel password contract and risks tenant selection drift | Depends on an undocumented session endpoint | Requires product-specific identity semantics | Rejected |
| Parse bearer JWT claims in the browser or product without an IdP verification call | Cannot safely centralize revocation and client semantics | Adds key-rotation and validation work to the product | Duplicates IdP responsibilities | Rejected |
| Authorization code with PKCE, confidential client exchange, and verified Keyverse introspection | Password stays at the IdP; claims are checked for this client | Fails closed when discovery, exchange, or introspection fails | Uses one compact actor projection | Accepted |

## Decision Outcome

Adopt Keyverse OpenID Connect authorization code with S256 PKCE. The browser submits one syntactically valid email address to `POST /api/login`; only after issuer discovery succeeds does it receive an authorization URL with a random state, code challenge, and the standard `login_hint`, then navigate to Keyverse. The verifier and state stay server-side for ten minutes; the browser receives only an `HttpOnly`, `SameSite=Lax`, secure state cookie. The callback compares the state in constant time, exchanges the code as a confidential client, then introspects the received access token over hostname-verifying TLS. The relying party uses Keyverse ADR-0009's closed `lineageweave-web` account-derived profile: `org` and `workspace` come from the authenticated account and `role` comes from that client's assigned roles. If Keyverse is unset or unavailable, login fails closed. The product Compose service consumes only operator-provisioned Keyverse values; the shipped Compose stand-in is a model-task proxy that clears known Keyverse and OIDC values and exposes no discovery, authorization, token, or introspection contract.

| Decision driver | Selected implementation |
| --- | --- |
| Relying-party configuration | Require `KEYVERSE_ISSUER`, `LINEAGEWEAVE_OIDC_CLIENT_ID`, `LINEAGEWEAVE_OIDC_CLIENT_SECRET`, and `LINEAGEWEAVE_OIDC_REDIRECT_URI`. Production endpoints stay HTTPS. HTTP is allowed only for an allowlisted loopback or Docker host-bridge Keyverse origin when both `LINEAGEWEAVE_DEV_MODE=1` and `LINEAGEWEAVE_COOKIE_SECURE=0`; the model worker is never an allowed issuer. |
| Metadata trust | Use issuer discovery; accept only the exact issuer and same-origin authorization, token, and introspection endpoints. |
| Callback integrity | Use S256 PKCE, a single-use server state record, a bounded state store, ASCII-safe constant-time state comparison, and a secure-by-default state cookie. |
| Token validation | Require `active`, exact issuer, audience containing this client, exact client identifier, a future expiry, and a usable subject, organization, workspace, and role or role list. |
| Actor projection | Map `sub` to account ID, `org` to legal-company code, `workspace` to PU code, and approved Keyverse roles to `reader`, `author`, `editor`, or `admin`; `member` becomes `reader`. |
| Session and API access | Store only an opaque local session whose TTL is capped by access-token expiry. Direct bearer requests use the same introspection and claim projection. |
| Browser boundary | Collect only an email address for `login_hint`; remove product account and password inputs. Missing or malformed email remains on the page with an accessible inline error. `POST /api/session` returns a redirect-required error; logout deletes only the local opaque session. The Compose stand-in cannot complete OIDC and never synthesizes a Keyman answer. |

A deployment operator must register the exact redirect URI and the reviewed
Keyverse ADR-0009 `lineageweave-web` profile before production traffic is
enabled. The product does not synthesize accounts, roles, or tenant values. No
configuration means a failed login start, not a fallback account form.

### Enforcement

The Compose worker is not an alternative local issuer. It contains no OIDC
issuer, client, account, role, organization, or workspace configuration; its
four IdP-shaped routes return `404` for every request. The release gate checks
both the worker source/Compose environment and those HTTP responses. An
independent boundary check rejects an issuer import or Docker build copy, and a
built-image check confirms no issuer module is shipped. A retained issuer-shaped
source artifact is not executable product code; its ownership and durable
disposition are separately governed by ADR-0001. A failed executable boundary
check prevents a Compose build or release; it is never waived by a
development-mode setting. Any future identity endpoint requires a separate ADR
and cannot be enabled as a product fallback.

### Current acceptance record (2026-08-13 and 2026-08-14)

A controlled local Keyverse 26.3.2 Compose run verified realm discovery, the
closed post-import account profile, a confidential `lineageweave-web` client
with the four ADR-0009 mappers, and a real account carrying the two reviewed
attributes plus its same-client role. The running LineageWeave service then
discovered that issuer and produced the expected authorization-code redirect
with S256 PKCE and a bounded state cookie. No account, tenant value, or token
was synthesized by the product.

This is not production-login evidence: the real Keycloak browser flow still
requires a user passkey, and no selected in-app browser surface was available to
complete that interaction. The former worker import, Docker copy, and inverted
test have been removed: the live worker now returns `404` for all four
IdP-shaped routes and its built image does not contain the retained source
artifact. That source remains unreferenced and unshipped, while its ownership
and durable archival disposition remain a separate release audit gate in
ADR-0001.

### Deployment configuration disposition (2026-08-14)

An interactive-shell inventory did not contain the direct-PostgreSQL or
Keyverse settings. A controlled Compose recovery therefore injected only the
already-authorized direct PostgreSQL runtime values at process launch and
reached a healthy product service; it did not inspect a secret store or retain
configuration in source. The product still had no usable production HTTPS
Keyverse configuration: a syntactically valid non-identifying login start
returned `503` with the generic unavailable response and created no session.
That is runtime and failure-boundary evidence, not an actual-account SSO
record. Operators must inject the approved Keyverse values through a deployment
secret/configuration mechanism, never tracked source. Release acceptance remains
open until an operator-provisioned instance completes the real Keyverse browser
journey and records the resulting authorized product session without retaining
credentials or account attributes.

## Consequences

Positive:

- A user authenticates at Keyverse rather than giving credentials to LineageWeave.
- ABAC/RBAC uses one verified actor for document, evidence, asset, KG, chat, and mutation routes.
- The confidential client does not expose its secret to the browser, and local sessions have a token-bounded lifetime.
- Browser and API access receive the same issuer/audience/client/expiry enforcement.

Trade-offs:

- Production requires Keyverse client registration, claims configuration, TLS trust, and an HTTPS redirect URI before login can succeed.
- Token introspection adds an IdP network call for browser callback and direct bearer access.
- This relying-party session does not replace Keyverse logout or global IdP session management.
- The local development actor and the local HTTP exception remain intentionally unsuitable for production and require explicit environment configuration; neither creates a Keyverse account or client.

## Risks and Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Callback state replay or cross-site substitution | Use a single-use, ten-minute state record, secure-by-default cookie, and constant-time comparison; require both development switches for the local HTTP exception | `begin_keyverse_login`, `complete_keyverse_login` |
| Token for another relying party is accepted | Require both audience membership and exact client identifier | `_actor_from_keyverse_access_token` |
| Issuer discovery or private CA tempts an insecure client | Require HTTPS, platform trust or an operator CA bundle, and fail closed; permit HTTP only for the explicit local Keyverse origin and never for the model worker | `_keyverse_metadata`, `verified_ssl_context` |
| Missing tenant or role mapper weakens authorization | Reject a claim projection without subject, organization, workspace, or mapped role | `_actor_from_value`, role map |
| Product stores a usable credential or durable access token | Store no browser password and only a random local session handle | React login surface, `_sessions` |
| Model worker is accidentally turned into a fallback IdP | Keep the worker health/model-only, remove issuer/client/account environment variables, and regress OIDC routes to 404 | `compose/http_standin.py`, `compose.yaml`, worker route test |
| A concurrent source change reintroduces an in-process issuer | Fail the executable boundary checks when an issuer import, build copy, or non-404 identity route appears; do not release until it is removed and the real Keyverse path is rechecked. Track any retained non-executable artifact through the ADR-0001 ownership gate. | `tests/test_identity_boundary_lock.py`, `tests/test_worker_contract.py`, built-image assertion |
| IdP outage prevents access | Return an unavailable or unauthorized response; do not mint a local fallback actor | login and callback routes |

## Rollback / Exit Strategy

1. Disable or revoke the LineageWeave Keyverse client and redirect URI; existing product sessions expire at their access-token boundary.
2. Remove the OIDC configuration to fail closed while preserving PostgreSQL source and analysis tables.
3. If a Keyverse claim mapping changes, pause the client, update the approved mapper, and exercise the contract tests before re-enabling login.
4. Retire the local development actor by removing its explicit environment configuration; it has no production session migration path.
5. Do not restore a browser password form or a product-specific session relay as a rollback mechanism.

## Affected Components

- `lineageweave_server.py`: discovery, PKCE request construction, token exchange, introspection, actor projection, bounded opaque sessions, login callback, logout, and bearer validation.
- `lineageweave.py`: shared verified TLS context used by Keyverse and model-gateway calls.
- `web/src/App.jsx` and `web/src/styles.css`: Keyverse SSO link and local logout action; no product password form.
- `tests/test_prototype_surfaces.py`: OIDC request, verified TLS, claim mapping, state mismatch, audience rejection, and React-boundary checks.
- Deployment configuration: issuer, confidential-client values, redirect URI, and optional Keyverse CA bundle.

## Verification and Monitoring

- Contract tests assert S256 PKCE, no client secret or verifier in the authorization URL, verified TLS on form posts, role/tenant projection, session lifetime, state mismatch rejection, wrong-audience rejection, and both explicit local-HTTP switches.
- Worker route tests assert that discovery, authorization, token, and introspection paths fail with `404`; the independent identity-boundary test rejects a worker issuer import or Docker copy, and the built-image assertion rejects shipment of an issuer module. A real Keyverse server remains the only issuer.
- The frontend build confirms the compiled React application has an email-first Keyverse login entry and no account or password form.
- `/api/session` reports the active verified actor only; `/api/queue/health` remains independent of identity secrets.
- Local development-mode API checks remain separate from production IdP
  acceptance. A production acceptance run requires a provisioned Keyverse
  issuer, client, redirect URI, ADR-0009 account-derived mapper profile, actual
  account role/attribute assignment, and cross-tenant/role-lifecycle evidence.

### Amendment: password-free product enrollment (2026-08-14)

The login gate now offers an optional product-owned enrollment flow for a
first-time account. `POST /api/register` either delegates to a configured
Keyverse registration adapter or, in explicitly local development mode,
creates the required-action request through the Keyverse Admin API. The
product opens the returned action page, extracts only the WebAuthn public-key
challenge and short-lived cookie state, and completes the browser-created
attestation through `POST /api/register/complete`. LineageWeave never receives
an account password, never chooses `org` or `workspace`, and never becomes an
issuer. Missing Keyverse transport, malformed challenge HTML, expired state,
and failed attestation all fail closed.

The current local browser gate completed password-free passkey enrollment at
the Keyverse-required loopback RP origin, then completed authorization code
with S256 PKCE, callback, and an authenticated LineageWeave session for the
same real local account. Structural session evidence confirmed both account
dimensions and one mapped role; no credential, token, account identifier, or
tenant value is recorded here. This closes loopback end-user acceptance while
leaving production HTTPS issuer, redirect, trust, and lifecycle acceptance
separate.

### Amendment: email-first Keyverse hand-off (2026-08-14)

The unauthenticated surface asks only for an 업무 이메일 and does not expose
OIDC, PKCE, SSO, tenant, role, or identity-provider implementation vocabulary
to end users. Its only explanatory sentence is “업무 이메일을 입력하고
계속하세요.”; the two actions are “계속하기” and “처음 이용하기.” An empty
value receives “업무 이메일을 입력해 주세요.” and a malformed value receives
“올바른 업무 이메일 주소를 입력해 주세요.” beside the field; neither state
starts navigation. The HTTP boundary independently normalizes and validates
the submitted value before any issuer discovery, so crafted direct `GET` or
`POST` login requests also fail with `400 invalid_email_address`.

A valid address is used only as the standard Keyverse `login_hint`. The
browser navigates only after the login-start response succeeds; configuration
or discovery failures stay on the product page with a generic message. The
product does not look up, provision, store, or disclose whether that address
has an account, and registration failures use a non-enumerating generic
message. The browser E2E runner now requires an operator-provided
`LINEAGEWEAVE_E2E_EMAIL` when no existing authenticated session is available;
this is a configuration prerequisite, not evidence of production acceptance.

The Compose product service may receive externally provisioned Keyverse values
through its operator-managed environment file. The model worker explicitly
overrides those identity values with empty values even though it reads the same
file for model configuration. This preserves one external issuer for the
product without allowing an issuer, client, or token configuration to leak into
the worker.

The current Compose runtime is healthy against its direct PostgreSQL source,
but its operator environment has no production HTTPS Keyverse values. A valid
non-identifying login start consequently returns the generic unavailable
response without navigation or session issuance. This is expected fail-closed
behavior, not login acceptance; no local issuer or development actor was used.

### Amendment: Keyverse-owned first-time onboarding (2026-08-15)

The customer-facing login gate no longer exposes a first-use button, browser
WebAuthn registration, or a product-side passkey journey. It has one action:
validate a business email and continue to the configured Keyverse authority.
Keyverse, not LineageWeave, owns account creation and passkey policy after that
redirect. This reduces a confusing second path without changing the product's
relying-party authorization-code, callback, session, or logout behavior.

The removed browser code and E2E enrollment switch are not a replacement for
actual Keyverse acceptance. The current unconfigured runtime continues to
return a generic in-page unavailable result for a valid email. A configured
production Keyverse run with a real business account remains required to prove
the hand-off, callback, session, logout, and any first-time onboarding policy.

The rebuilt direct-PostgreSQL runtime renders exactly one login action and no
first-use or protocol label. Its browser check confirmed distinct empty and
invalid-email guidance, followed by the same generic in-page `503` result for
a valid non-identifying address. The unauthenticated `POST /api/register` and
`POST /api/register/complete` paths now return `404`, so the product cannot
provision or relay a passkey ceremony. The current source gate passed 333 tests
with 7,358 statements and 2,838 branches at 100 percent line-and-branch
coverage; the React production build, database health check, and four
issuer-shaped route rejections also passed. None of this is a substitute for
configured Keyverse acceptance.

### Amendment: complete product-side enrollment removal (2026-08-15)

The earlier browser-facing retirement is now enforced in the product runtime
as well: the server no longer contains account-provisioning, local email-capture,
WebAuthn challenge parsing, or attestation-relay code. `GET` and `POST` for
both `/api/register` and `/api/register/complete` return `404` before session
authorization. This is a relying-party boundary decision, not a replacement
identity service: Keyverse remains the only owner of first-time account and
passkey policy.

The current full source gate passed 331 tests with 7,095 statements and 2,760
branches at 100 percent line-and-branch coverage. The Compose identity guard
and React production build passed. The retained issuer-shaped audit artifact
was not changed and remains neither an executable product dependency nor
production Keyverse acceptance evidence.

## References

Internet Engineering Task Force. (2015). *Proof key for code exchange by OAuth public clients* (RFC 7636). https://www.rfc-editor.org/rfc/rfc7636

Internet Engineering Task Force. (2025). *Best current practice for OAuth 2.0 security* (RFC 9700). https://www.rfc-editor.org/rfc/rfc9700

OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set 2*. https://openid.net/specs/openid-connect-core-1_0.html

ContextualWisdomLab. (2026). *Keyverse relying-party documentation and claim-mapper configuration*. Local repository material consulted for this decision.

LineageWeave. (2026). *ADR-0001: Run LineageWeave as a direct-PostgreSQL governed product*. `docs/planning/adrs/0001-lineageweave-runtime-and-governance.md`.

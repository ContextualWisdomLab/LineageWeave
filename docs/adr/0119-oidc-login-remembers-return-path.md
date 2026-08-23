# ADR 0119 — Login remembers a safe return path and does not mount admin settings

**Decision status:** Accepted
**Date:** 2026-08-24
**Amends:** [ADR 0109](0109-oidc-deep-link-state-recovery.md)

## Context

ADR 0109 recovers `/?post=<id>` across OIDC callback contexts by persisting a
validated same-origin path before redirect and restoring it on callback.
The unauthenticated login control later stopped calling
`rememberOidcReturnUrl` / `returnUrlFromLocation`, so the callback helpers
had nothing to restore when provider state was omitted. The same login shell
also type-checked an `AdminPanel` with an undefined access token, which
broke the frontend production build (`tsc -b`) and would have asked a
signed-out buyer to save tenant settings.

## Decision

- The unauthenticated **Log in** control takes `returnUrl` from
  `returnUrlFromLocation()`, calls `rememberOidcReturnUrl(returnUrl)`, then
  starts `signinRedirect({ state: { returnUrl } })`. Raw
  `pathname + search` concatenation is not a return URL.
- Tenant admin settings mount only after authentication has produced an
  access token. The signed-out login shell does not render `AdminPanel`.
- Do not invent a leftover score, a theta, or a tenant name. Synthetic
  fixtures only.

## Consequences

Opening a shared post link, logging in, and landing on that post works when
the provider omits application state. `pnpm run build` type-checks the login
shell. Independent of leftover-map PRs (#481, #485, #518, #519, #521, #522).

## References

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

# ADR 0025 — Fail-closed Keyverse identity port

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

LineageWeave's demo login is a local Keycloak realm with synthetic
accounts (ADR 0001). The organization's production IdP is
[Keyverse](https://github.com/ContextualWisdomLab/keyverse): passwordless
OIDC on Keycloak plus an account-unification admin service that
publishes `GET /healthz` as `{status: "ok"}`. Until this slice, Demo
Analyst had no buyer-facing identity-port status: a down Keyverse was
silent, and nothing stopped a later writer from inventing an issuer,
account, or corp code.

This ADR does not replace the synthetic demo Keycloak login, does not
register LineageWeave as a production relying party, and does not bind
demo tokens to a production Keyverse tenant.

## Decision

1. Consume Keyverse only through `KeyverseClient` and the published
   `GET /healthz` envelope. Never read Keyverse tables. Never copy an
   issuer, account, token, or client registration.
2. The default transport raises `KeyverseNotAvailable`. HTTP 4xx/5xx,
   timeout, network, non-https, and an unknown envelope fail closed.
3. Project only `ready=true` when `status` is exactly `ok`. Extra
   healthz fields are dropped.
4. `GET /api/identity` (`post_read`) returns `unavailable` +
   `keyverse_not_available` + `ready=false` when the port is down.
5. After login, Identity sits above Calendar. Unavailable copy is
   **Identity · Keyverse not available**. An accepted probe names
   readiness only — click does not invent a login.

## Consequences

`KEYVERSE_BASE_URL` empty keeps the fail-closed transport. Demo login
stays on the synthetic Keycloak realm. Rankings stay on ADR 0024 /
#220. Mailbox stays on ADR 0020 / #217. Conversations stay on ADR 0021
/ #219. TEPP stays on #214. Registering LineageWeave as a Keyverse RP
is a later slice.

## References

Contextual Wisdom Lab. (2026). *cwl-idp — ecosystem central IdP*
[Software documentation]. https://github.com/ContextualWisdomLab/keyverse

Contextual Wisdom Lab. (2026). *Relying-party onboarding* [Keyverse
documentation].
https://github.com/ContextualWisdomLab/keyverse/blob/main/docs/rp-onboarding.md

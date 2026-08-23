# ADR 0109: Recover authenticated deep links across OIDC callback contexts

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0069](0069-member-locale-preference.md), [0028](0028-keyverse-oidc-provider.md)

## Context

The Buyer can be opened directly at `/?post=<id>`. The OIDC provider callback
may omit application state or complete in a browser context where the original
tab's `sessionStorage` is not available. Falling back to `/` loses the post
deep link and presents the unauthenticated language/login surface again, even
when the member's OIDC session is otherwise valid.

## Decision

- Keep the OIDC `state.returnUrl` as the first recovery source.
- Accept only a direct same-origin path, one bounded serialized object, or one
  object value. Never recursively parse JSON-encoded strings; reject serialized
  state and return paths longer than 4,096 characters before further handling.
- Persist the same validated same-origin path in both `sessionStorage` and
  `localStorage` before redirecting to OIDC. `localStorage` is only a bounded
  recovery fallback, not an authentication or authorization store.
- The signed-out **Log in** control computes that path with
  `returnUrlFromLocation()`, persists it with `rememberOidcReturnUrl`, and
  passes the same value in `signinRedirect` state.
- Tenant admin settings mount only after authentication provides an access
  token; the signed-out login shell never renders `AdminPanel`.
- On callback, remove the key from both stores and use session storage before
  local storage. Reject external and protocol-relative URLs.
- Keep member language preference account-scoped in
  `user_account.preferred_locale`; this ADR does not move locale state into the
  post URL, browser storage, or a `user_account + post_id` key.

## Consequences

Opening a shared post link survives a missing OIDC state payload or a changed
storage context without losing the post. A stale internal return path is
removed at callback, and authorization still comes only from the authenticated
OIDC token and backend ABAC checks.

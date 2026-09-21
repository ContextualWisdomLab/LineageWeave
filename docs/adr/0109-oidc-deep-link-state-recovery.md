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

The authorization endpoint can return either a successful code response or an
OAuth error response. Those response fields are one-time protocol artifacts,
not application navigation state. If a failed callback is turned back into a
remembered return URL, provider error fields can be replayed on the next
successful sign-in and can expose provider detail in a product-controlled URL.
A provider callback is also rooted at the configured redirect URI rather than
the original buyer deep link, so rebuilding retry state from the failed
callback alone can overwrite the path that was remembered before redirect.

## Decision

- Keep the OIDC `state.returnUrl` as the first recovery source.
- Accept only a direct same-origin path, one bounded serialized object, or one
  object value. Never recursively parse JSON-encoded strings; reject serialized
  state and return paths longer than 4,096 characters before further handling.
- Persist the same validated same-origin path in both `sessionStorage` and
  `localStorage` before redirecting to OIDC. `localStorage` is only a bounded
  recovery fallback, not an authentication or authorization store.
- On every return-path admission boundary — current browser location,
  `state.returnUrl`, `sessionStorage`, and `localStorage` — and before writing a
  return path back to storage, remove authorization-response artifacts: `code`,
  `state`, `session_state`, `iss`, `error`, `error_description`, and
  `error_uri`. Preserve unrelated same-origin product query parameters and the
  fragment. This also cleans values persisted by an older client before this
  boundary existed.
- When retrying while the browser is still on an OIDC success/error callback,
  prefer the validated path remembered before redirect over the callback's
  sanitized redirect-URI path. Treat `code`, an OAuth `error*` field, or OIDC
  response metadata such as `session_state`/`iss` as callback evidence;
  `state` alone is scrubbed as reserved protocol data but does not authorize
  stale browser storage to override an otherwise current product URL.
- Ordinary product navigation without callback evidence continues to derive
  its return path from the current location.
- On callback, remove the key from both stores and use session storage before
  local storage. Reject external and protocol-relative URLs.
- Keep member language preference account-scoped in
  `user_account.preferred_locale`; this ADR does not move locale state into the
  post URL, browser storage, or a `user_account + post_id` key.

## Consequences

Opening a shared post link survives a missing OIDC state payload or a changed
storage context without losing the post. A failed provider callback no longer
replaces the pre-redirect deep link with `/` merely because the callback was
rooted at the redirect URI, while an unrelated lone `state` query cannot make
stale return-path storage win over current product navigation. Successful and
failed authorization response fields are not minted into a later product
return path, including when an older stored/state value is recovered. A stale
internal return path is removed at callback, and authorization still comes only
from the authenticated OIDC token and backend ABAC checks.

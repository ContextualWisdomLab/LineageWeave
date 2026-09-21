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

The browser also accepts arbitrary product query parameters on the SPA root.
A response-shaped query name such as `code` or `error` therefore cannot, by
itself, prove that the current URL is the response to the OIDC transaction that
created remembered return-path storage. LineageWeave sends `state` on the
Authorization Code request; OAuth 2.0 and OpenID Connect require that value to
be returned on both success and error responses when it was present in the
request. A valid Authorization Code response also has a primary outcome member:
`code` for success or `error` for failure. `session_state`, `iss`,
`error_description`, and `error_uri` are ancillary metadata and cannot establish
a success or error response by themselves. Remembered-path precedence therefore
needs returned `state` plus `code` or `error`; either side alone is insufficient.

A lexical leading-slash check is not sufficient to prove that a candidate is a
same-origin path. WHATWG URL parsing treats backslashes as authority separators
for special schemes, so a value such as `/\\example.invalid/path` can begin
with a single slash yet parse to a different origin. Reconstructing only the
parsed pathname would then silently turn an external-shaped value into a new
local deep link rather than rejecting the invalid admission.

## Decision

- Keep the OIDC `state.returnUrl` as the first recovery source.
- Accept only a direct same-origin path, one bounded serialized object, or one
  object value. Never recursively parse JSON-encoded strings; reject serialized
  state and return paths longer than 4,096 characters before further handling.
- Validate return paths after WHATWG parsing against the product origin, not
  only by string prefix. Reject any candidate whose parsed origin differs;
  never strip an unexpected authority and re-mint only its pathname as local.
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
  sanitized redirect-URI path only when `state` is present together with a
  primary Authorization Code response member: `code` for success or `error`
  for failure. `state` alone, `code`/`error` without `state`, and ancillary
  metadata (`session_state`, `iss`, `error_description`, `error_uri`) without a
  primary outcome are still scrubbed as reserved protocol data, but none of
  those incomplete shapes authorizes stale browser storage to override current
  product navigation. This follows RFC 6749 §§4.1.2 and 4.1.2.1: success
  responses carry `code`, error responses carry `error`, and either response
  returns `state` when the request supplied it. OpenID Connect metadata does
  not replace that primary OAuth response member.
- Ordinary product navigation without correlated callback evidence continues
  to derive its return path from the current location.
- On callback, remove the key from both stores and use session storage before
  local storage. Reject external and protocol-relative URLs.
- Keep member language preference account-scoped in
  `user_account.preferred_locale`; this ADR does not move locale state into the
  post URL, browser storage, or a `user_account + post_id` key.

## Consequences

Opening a shared post link survives a missing OIDC state payload or a changed
storage context without losing the post. A failed provider callback no longer
replaces the pre-redirect deep link with `/` merely because the callback was
rooted at the redirect URI, while incomplete response-shaped query combinations
cannot make stale return-path storage win over current product navigation. A
remembered path is preferred only for the correlated `state + code` or
`state + error` shapes. Successful and failed authorization response fields are
not minted into a later product return path, including when an older
stored/state value is recovered. Inputs that only look path-relative before
parsing but resolve to another origin are rejected instead of being host-stripped
into a different local path. A stale internal return path is removed at callback,
and authorization still comes only from the authenticated OIDC token and backend
ABAC checks.

## References

Hardt, D. (2012). *The OAuth 2.0 authorization framework* (RFC 6749). Internet Engineering Task Force.

OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set 2*.

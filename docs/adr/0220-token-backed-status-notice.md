# ADR 0220: Share one token-backed status notice

- Status: Accepted
- Date: 2026-08-25
- Issue: #611
- Supersedes closed-branch ADR 0134 for current protected `main` only

## Context

Issue #611 decomposes closed PR #490 without replaying that 321-file tree.
Closed-branch ADR 0134 required a shared token-backed exception surface with
success, unavailable, and retry states. Protected `main` already sanitizes
provider failures (ADR 0123) and has ad hoc `role="alert"` / placeholder copy,
but it has no shared accessible notice. Calendar's Naruon fail-closed path
(ADR 0203) currently renders the next action as a second placeholder without
an accessible status.

## Decision

Add one `StatusNotice` component under `frontend/src/components/` that:

1. Accepts only `success`, `unavailable`, or `retry`.
2. Distinguishes those kinds by visible label text and glyph shape, not color
   alone (WCAG 1.4.1). Color uses the existing ADR 0099 badge-status tokens.
3. Uses a named `region` (`role="region"` plus `aria-label`) for success
   and unavailable so the notice does not collide with App live-region
   uniqueness (`getByRole("status")`). Retry uses `role="alert"`.
   Unavailable is missing evidence, not a transport failure.
4. Renders caller-supplied message and optional next-action copy. It never
   interpolates provider payloads, credentials, or raw HTTP bodies (ADR 0123).
5. Shows a retry control only on the retry kind when the caller supplies
   `onRetry`.

The first migrated product flow is the Calendar Naruon fail-closed path.
Do not copy closed-branch exception classes or Storybook inventories from
PR #490. Later unavailable flows migrate one at a time.

## Consequences

- Calendar names the missing Naruon projection and the next action in one
  accessible notice while commitments remain clickable.
- Storybook `Chrome/StatusNotice` covers success, unavailable, and retry.
- New product failures must reuse this component instead of a second
  placeholder or inline `role="alert"` with raw hex.

## References — APA 7th

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023). *ARIA in HTML* (W3C Recommendation).
https://www.w3.org/TR/html-aria/

National Institute of Standards and Technology. (2020). *Security and privacy
controls for information systems and organizations* (NIST Special Publication
800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5

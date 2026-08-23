# ADR 0134: Token-backed exception messages name a next reader action

- Status: Accepted
- Date: 2026-08-23
- Figma: File ID `1Su3lDRmiZdcUs47t1QwIX`
- Related: [0002](0002-figma-access-boundary.md), [0099](0099-badge-and-accent-color-tokens.md), [0118](0118-uiux-standard-guide-v3-design-overhaul.md), [0123](0123-provider-error-boundary.md)

## Context

Reader-facing failures were often a color-only red paragraph (`<p class="error">`).
That surface did not identify the failure in text independent of color, did not
name a next action, and sometimes interpolated a raw exception, OIDC diagnostic,
or HTTP 5xx payload. WCAG 2.2 requires identifying input errors in text (3.3.1),
suggesting a correction (3.3.3), and announcing status changes through a
programmatic live region (4.1.3). ADR 0123 already forbids exposing provider
payloads at the API and browser-client boundary (CWE-209); the workspace UI
must not reintroduce that leak by rendering `String(err)`, `err.stack`, or
`auth.error.message`.

The Figma file recorded in ADR 0002 and ADR 0118 remains the design source.
This decision applies that file to exception feedback only; it does not restyle
the rest of the workspace.

## Decision

1. Reuse the shipped unavailable pattern (`SummaryStatus` title + description +
   optional detail + retry) as `ExceptionAlert`. Do not invent a second visual
   language, toast, or snackbar.
2. Style that surface with light and dark `--color-exception-{background,border,accent,text,heading}`
   tokens. Contrast is not color-only: heading text, a left accent border, and
   a filled background identify the failure. Recovery controls keep
   `--size-control-min` and the existing focus-visible treatment.
3. Map transport and unexpected failures through `productExceptionCopy` before
   render. HTTP 5xx and status-0 keep the sanitized `BackendError` message.
   Raw exception types, stacks, and provider payloads become
   `{action} could not be completed.` Client-actionable 4xx validation text is
   retained only when it is not a raw exception.
4. Every reader-facing failure names a next action in copy (retry, continue
   with saved evidence, log in, correct highlighted fields). When recovery is
   possible, expose a focusable control. Failures use `role="alert"`;
   processing and empty states stay `role="status"`.
5. Sign-in failures never render the OIDC `error.message`. They show a product
   title, a log-in next action, and a Log in control.

## Consequences

- Auth, board, popup/panel fetch, Ask/chat, summary unavailable, admin form,
  source research, and cited-evidence miss share one token-backed pattern.
- Storybook records unavailable, retryable transport, form-field, auth, and
  continue-with-saved-evidence scenes.
- ADR 0123 remains the payload policy. This ADR is the reader-facing
  presentation of that fail-closed copy.

## References — APA 7th

MITRE. (2026). *CWE-209: Generation of error message containing sensitive
information*. https://cwe.mitre.org/data/definitions/209.html

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2024). *Error identification* (Understanding
SC 3.3.1). https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html

World Wide Web Consortium. (2024). *Error suggestion* (Understanding SC
3.3.3). https://www.w3.org/WAI/WCAG22/Understanding/error-suggestion.html

World Wide Web Consortium. (2024). *Status messages* (Understanding SC
4.1.3). https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html

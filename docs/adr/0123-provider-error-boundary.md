# ADR 0123: Provider failures never become product error payloads

- Status: Accepted
- Date: 2026-08-21

## Context

Provider responses and exception messages can contain credentials, gateway
diagnostics, prompts, model output, or other internal transport detail. A
provider outage is not buyer evidence and must not be returned as an API error
or persisted as a durable ingestion detail.

## Decision

Every contextual-orchestrator, VISION, search, RankWeave, and TEPP boundary
returns a stable product-level unavailable message. Route handlers catch both
known transport/parse failures and unexpected provider exceptions, while
retaining the original exception only as an in-process chained cause for
operator logging. Provider response parsers use generic validation errors and
never interpolate the raw response into an exception message. All
OpenAI-compatible chat-completion consumers use the shared
``chat_completion_content`` validator, so malformed ``choices`` envelopes
cannot escape as raw ``KeyError`` or type-error payloads from a library
boundary.

The browser API client is a second trust boundary: HTTP 5xx details are
discarded, and transport failures become a stable status-0 client error
before any UI handler can render them. Client-error details remain available
only for actionable validation or authorization responses.

Missing or malformed evidence remains unavailable; it is never converted into
a fabricated negative result. Existing input-validation errors outside a
provider boundary retain their client-actionable 422 detail.

Provider admission deferral is a narrow control exception. HTTP 503
`no_viable_agent` and HTTP 429 `rate_limit_exceeded` become a retryable worker
signal only when the orchestrator returns the same positive integer delay in
both `Retry-After` and `error.detail.retry_after_seconds`. A missing,
malformed, or conflicting value remains an ordinary unavailable response.
This consumes the upstream contract introduced by contextual-orchestrator PR
#907 without exposing its error body to the product surface.

## Consequences

- API clients receive a safe retry/configuration action rather than provider
  internals.
- Browser clients cannot turn an upstream 5xx detail or transport exception
  into buyer-visible provider diagnostics.
- Server-side debugging keeps exception chaining without exposing it to buyers.
- Malformed provider success envelopes fail closed with a stable validation
  error before any channel parser sees them.
- Regression tests exercise unexpected exceptions, not only known transport
  subclasses, and assert that provider secrets do not appear in responses.

## References — APA 7th

National Institute of Standards and Technology. (2020). *Security and privacy
controls for information systems and organizations* (NIST Special Publication
800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5

OWASP Foundation. (2025). *Improper error handling*. OWASP Application
Security Verification Standard. https://owasp.org/www-project-application-security-verification-standard/

MITRE. (2026). *CWE-209: Generation of error message containing sensitive
information*. https://cwe.mitre.org/data/definitions/209.html

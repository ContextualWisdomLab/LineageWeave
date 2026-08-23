# ADR 0123: Provider failures never become product error payloads

- Status: Accepted
- Date: 2026-08-21

## Context

Provider responses and exception messages can contain credentials, gateway
diagnostics, prompts, model output, or other internal transport detail. A
provider outage is not buyer evidence and must not be returned as an API error
or persisted as a durable ingestion detail.

## Decision

Every contextual-orchestrator, OIDC/JWKS, RankWeave, and TEPP boundary returns
a stable product-level unavailable message. Route handlers and configured
transports catch known transport/parse failures and record only a stable,
secret-free message, while retaining the original exception as an in-process
chained cause for operator logging. Provider chat-completion consumers use the
shared `chat_completion_content` validator (`lineageweave/http_client.py`), so
a malformed `choices` envelope cannot escape as a raw `KeyError` or
type-error payload from a library boundary.

`backend/app/auth.py` reports OIDC JWKS fetch and access-token decode failures
as a fixed "identity provider unavailable" / "invalid access token" detail
instead of interpolating the issuer URL or the underlying `PyJWTError` text.
`backend/app/analysis_run_start.py` reports a TEPP transport failure as a
fixed "TEPP transport unavailable" `TeppNotAvailable` detail instead of the
raw transport exception. `backend/app/main.py`'s post-chat and Ask Agent
routes catch `TypeError` alongside the existing transport/parse exception
types, since `chat_completion_content` raises `TypeError` for a malformed
provider envelope, and both routes report the same stable
next-action-safe detail regardless of which exception was raised.

Missing or malformed evidence remains unavailable; it is never converted into
a fabricated negative result. Existing input-validation errors outside a
provider boundary retain their client-actionable detail.

## Consequences

- API clients and persisted ingestion failure details receive a safe
  retry/configuration action rather than provider internals.
- Server-side debugging keeps exception chaining without exposing it to
  buyers.
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

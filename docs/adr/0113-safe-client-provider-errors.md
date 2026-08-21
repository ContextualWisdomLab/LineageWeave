# ADR 0113: Keep provider failures out of buyer-facing client errors

- Status: Accepted
- Date: 2026-08-21

## Context

The API client receives a backend `detail` field for failed requests. A
provider outage can otherwise place an upstream exception, credential hint,
or stack-trace fragment in that field, and existing UI error handlers render
`Error` values directly. The backend has its own stable provider boundary,
but the browser is a separate trust boundary and must remain safe if an old
or misconfigured backend leaks provider detail.

## Decision

1. `BackendError` replaces details from HTTP 5xx responses with a stable
   retry message.
2. Network failures become `BackendError` with status `0` and a stable retry
   message instead of exposing the browser or transport exception.
3. Client-error details remain available for actionable validation and
   authorization responses; provider failures are never buyer-facing.

This is a defense-in-depth boundary. Provider calls still go through
contextual-orchestrator, and server-side provider error handling remains
normative under the relevant backend ADRs.

## Verification

`frontend/src/api.test.ts` proves that an upstream-looking 502 detail and a
transport exception are both converted to stable client messages without
persisting or displaying the original text.

## References

National Institute of Standards and Technology. (2020). *Security and
privacy controls for information systems and organizations: NIST Special
Publication 800-53 Revision 5*. https://doi.org/10.6028/NIST.SP.800-53r5

OWASP Foundation. (2025). *Application Security Verification Standard 5.0.0*.
https://owasp.org/www-project-application-security-verification-standard/

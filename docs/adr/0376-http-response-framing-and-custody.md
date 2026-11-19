# ADR 0376: Complete native HTTP framing and explicit response custody

- Status: Proposed
- Scope: Private mechanical repair proposal, not adopted runtime policy
- Related: ADR 0122, ADR 0083

## Context

The shared HTTP client reads Content-Length bytes with HTTPResponse.read(n).
Native bounded reads may return short bytes at EOF without raising
IncompleteRead. When the native parser selected chunked transfer framing,
reading the conflicting Content-Length amount can stop at a valid JSON prefix
before the terminal chunk is validated. HTTPConnection.getresponse can detach
a will_close response, so connection.close alone does not close its makefile.

Synthetic native-parser regressions reproduce both boundaries. ASGI Post Chat
controls also show that incomplete frames can reach answer INSERT generation
and non-error telemetry. Recording SQL is not a committed database result.

## Proposed decision

Retain the native HTTPResponse framing decision: chunked bodies ignore the
conflicting Content-Length header and read through native terminal framing,
subject to the caller's unchanged optional decoded-body byte cap. A nonchunked
Content-Length remains validated with the existing nonnegative/cap rules, and
an early EOF is rejected by comparing the returned byte count with the
validated declared length. Lengthless responses retain their current EOF and
byte-cap behavior. This is not strict rejection of every conflicting header,
a new request timeout, a new global cap, or a custom HTTP parser.

The request owns both its returned response and its connection and closes
both on success and failure. Existing reader-safe transport errors, TLS trust,
request metadata, configured endpoints, model routing, auth, retries and
telemetry policy remain unchanged. ADR 0122 already requires invalid bodies
to produce error spans; this proposal restores rejection before decoding and
answer persistence rather than creating a new telemetry policy.

## Acceptance boundaries

Require native declared/lengthless/chunked controls, incomplete-frame and
byte-cap negatives, detached-response closure, Post Chat zero-write/error-span
controls and affected existing consumers. Preserve original RED receipts.
Independent whole-successor review, source-owner adoption, canonical CI,
normal protected publication and deployed authenticated/provider journeys are
separate obligations. No status promotion is implied by private selected tests.

# ADR 0277: Bounded Customer Master read

- Status: Accepted
- Date: 2026-08-31

## Context

Customer Master returned as many as one hundred customer groups and one
hundred author groups, each carrying as many as twenty related Posts.  The
browser rendered only the first thirty groups but still downloaded the whole
response.  With 43,189 Posts the response was 274,761 bytes and required
1.4--1.7 seconds.

## Decision

Customer and author groups are trigger-maintained in narrow read projections
using the same source eligibility and ABAC dimensions as the authoritative
Posts.  Counts are adjusted in the source write transaction; no cached count
may outlive the fact that produced it.  Reads return twenty groups by default,
at most fifty, with independent count-ordered keyset cursors for customer and
author groups.  The payload includes exact authorized totals over all groups.

The group summary does not carry related Posts.  Opening a group starts an
independent bounded related-Post read, ordered by `(created_at, post_id)`, and
exposes a group-bound continuation.  It is never silently truncated or
replaced by an approximate sample.  The UI requests the first page only when
the reader opens the group and requests continuation only when more evidence
exists.

Readiness follows initialization of every pool connection's projection paths
and the issuer-bound JWKS cache.  A signing-key miss still performs the
existing one-time forced refresh, so startup warming does not pin a rotated
key or add an arbitrary cache lifetime.

## Consequences

Response size and serialization are bounded without changing membership,
counts, provenance, or authorization.  Existing source identifiers remain
hints rather than customer bindings.  Runtime acceptance measures cold and
warm complete-response latency against ADR 0272.

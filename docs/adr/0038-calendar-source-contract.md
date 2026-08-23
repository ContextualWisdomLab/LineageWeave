# ADR 0038: Separate external calendar events from internal commitments

- Status: Superseded in part by ADR 0143
- Date: 2026-08-18

## Context

The buyer Calendar destination needs both external calendar observations and
actionable records derived from LineageWeave posts. They have different
ownership and evidence boundaries. The application already stores authorized
commitments and issue tickets, while the first external adapter read a custom
JSON `GET {CALDAV_BASE_URL}/events` feed.

That feed was not a CalDAV client or server contract. It did not implement RFC
4791 WebDAV discovery/REPORT, RFC 5545 recurrence and timezone semantics, RFC
6578 synchronization, provider revisions, or provider authorization. Product
and code language must not represent it as shipped CalDAV interoperability.

## Original decision retained

The Buyer Calendar returns two independent collections:

- `events`: externally observed calendar occurrences; and
- `commitments`: the existing authorized internal commitment projection,
  filtered by the requesting account's `post_read` RBAC and post ABAC rules.

When the external calendar channel is unset or temporarily unavailable,
`events` is empty and the internal commitments remain available. The backend
never invents an external event.

LineageWeave does not add a second calendar database, CalDAV server, provider
credential store, or writeback engine.

## Superseding decision

ADR 0143 replaces the custom `/events` transport and CalDAV naming with a
versioned, read-only Naruon calendar projection contract. Naruon is the authority
for customer-owned provider access, source registry, synchronization, provider
revisions, writeback, retries, and reconciliation. LineageWeave consumes only
bounded, already-authorized `observed` occurrence projections.

The original separation between `events` and `commitments` remains mandatory.
An external event is not converted to an internal issue or commitment without a
separate source-grounded LineageWeave decision and evidence trail.

## Consequences

- The Calendar remains useful with authorized commitment data when Naruon is
  unavailable.
- External observations cannot be mistaken for post-grounded commitments.
- Product documentation no longer represents a custom JSON feed as CalDAV.
- Runtime activation waits for Naruon's matching read endpoint and service
  audience; absence continues to fail closed rather than fabricate events.

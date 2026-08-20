# ADR 0038: Separate CalDAV events from internal commitments

- Status: Accepted
- Date: 2026-08-18

## Context

The buyer Calendar destination needs both external calendar events and
actionable records derived from LineageWeave posts. They have different
ownership and evidence boundaries. PR #251 defines CalDAV as an independent
consumer port, while the current application already stores authorized
commitments and issue tickets.

## Decision

`GET /api/calendar` returns two independent collections:

- `events`: events read from `CALDAV_BASE_URL/events` through
  `lineageweave.caldav_client`; malformed external rows are ignored.
- `commitments`: the existing authorized internal commitment projection,
  filtered by the requesting account's `post_read` RBAC and post ABAC rules.

When CalDAV is unset or temporarily unavailable, `events` is empty and the
response includes a next action in `calendar_sources`; the internal
commitments remain available. The backend never invents an external event.

This checkpoint does not add a second calendar database. A persistent event
store and sync history may be added when offline access, change tracking, or
CalDAV write-back becomes a product requirement.

## Consequences

- The Calendar screen is useful with the existing synthetic commitment data,
  even without an external calendar server.
- External events cannot be mistaken for post-grounded commitments.
- CalDAV transport failures do not turn the entire buyer surface into a
  fail-closed blank screen.

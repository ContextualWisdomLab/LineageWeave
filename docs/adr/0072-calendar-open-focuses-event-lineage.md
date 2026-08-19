# ADR 0072: Opening a Calendar commitment focuses Event Lineage

- Status: Accepted
- Date: 2026-08-19

## Context

Board Weekly VOC opens already focus Event Lineage (ADR 0071). Calendar is
the other buyer destination that opens a source post from an authorized
commitment. That open was a home-list open: the popup body appeared and
Event Lineage did not take focus.

## Decision

Opening a commitment on Calendar is a `fromCalendar` open. That open reuses
the Event Lineage focus path used by report-member and Weekly VOC opens:

- Calendar names the next action: authorized commitments are current; open
  a commitment to read Event Lineage.
- The popup Event Lineage heading takes focus.
- The popup names the opened post as current in Event Lineage and tells
  the buyer to read Keyman and evaluation next.

A Board home-list open does not focus Event Lineage and does not add that
copy. A `?post=` deep link is still a home-list open.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). Calendar
does not invent a CalDAV event (ADR 0038).

## Consequences

- Calendar, Weekly VOC, and report-member opens share one focus contract.
- Closing the popup clears the Calendar open flag.

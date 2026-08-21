# ADR 0095: Opening a Customer master related post focuses Event Lineage

- Status: Accepted
- Date: 2026-08-19

## Context

Board Weekly VOC and Calendar commitment opens already focus Event Lineage
(ADR 0093 / ADR 0134). Customer master is the remaining buyer GNB destination
that opens an authorized related post. That open was a home-list open: the
popup body appeared and Event Lineage did not take focus.

## Decision

Opening a related post on Customer master is a `fromCustomerMaster` open.
That open reuses the Event Lineage focus path used by report-member,
Weekly VOC, and Calendar opens:

- Customer master names the next action: authorized customer entities are
  current; open a related post to read Event Lineage.
- The popup Event Lineage heading takes focus.
- The popup names the opened post as current in Event Lineage and tells
  the buyer to read Keyman and evaluation next.

A Board home-list open does not focus Event Lineage and does not add that
copy. A `?post=` deep link is still a home-list open.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). Customer
master does not invent a customer or a parent (ADR 0037 / ADR 0010).

## Consequences

- Customer master, Calendar, Weekly VOC, and report-member opens share one
  focus contract.
- Closing the popup clears the Customer master open flag.

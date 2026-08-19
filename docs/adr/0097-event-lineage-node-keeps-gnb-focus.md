# ADR 0097: A linked Event Lineage node keeps GNB focus

- Status: Accepted
- Date: 2026-08-19

## Context

Opening a Board Weekly VOC post, Calendar commitment, Customer master
related post, Ask Agent cited post, or report member already focuses
Event Lineage (ADR 0093 / ADR 0094 / ADR 0095 / ADR 0096). Clicking a
linked Event Lineage DAG node then called `selectPost` without those
flags. The popup switched records and dropped the GNB focus contract:
Keyman and evaluation were no longer named next.

## Decision

A popup-internal Event Lineage DAG open reuses the originating GNB
flags (`fromReportMember`, `fromWeeklyVoc`, `fromCalendar`,
`fromCustomerMaster`, `fromAskAgent`):

- The popup Event Lineage heading stays focused.
- The popup names the newly opened post as current in Event Lineage
  and tells the buyer to read Keyman and evaluation next.

A Board home-list DAG walk does not focus Event Lineage and does not
add that copy. Closing the popup still clears the originating flags.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). No
cited post, customer, week, or CalDAV event is invented.

## Consequences

- GNB destinations share one Event Lineage focus contract across the
  first open and a linked DAG walk from that popup.
- A home-list DAG walk stays a home-list open.

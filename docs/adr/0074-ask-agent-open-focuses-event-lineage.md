# ADR 0074: Opening an Ask Agent cited post focuses Event Lineage

- Status: Accepted
- Date: 2026-08-19

## Context

Board Weekly VOC, Calendar, and Customer master opens already focus Event
Lineage (ADR 0071 / ADR 0072 / ADR 0073). Ask Agent is the remaining buyer
GNB destination that opens an authorized cited post. That open was a
home-list open: the popup body appeared and Event Lineage did not take
focus.

## Decision

Opening a cited post on Ask Agent is a `fromAskAgent` open. That open
reuses the Event Lineage focus path used by report-member, Weekly VOC,
Calendar, and Customer master opens:

- After an authorized answer, Ask Agent names the next action: cited posts
  are current; open a cited post to read Event Lineage.
- The popup Event Lineage heading takes focus.
- The popup names the opened post as current in Event Lineage and tells
  the buyer to read Keyman and evaluation next.

A Board home-list open does not focus Event Lineage and does not add that
copy. A `?post=` deep link is still a home-list open.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). Ask Agent
does not invent a cited post (ADR 0039).

## Consequences

- Ask Agent, Customer master, Calendar, Weekly VOC, and report-member
  opens share one focus contract.
- Closing the popup clears the Ask Agent open flag.

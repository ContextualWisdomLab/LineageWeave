# ADR 0075: GNB destination opens land Keyman and evaluation under Event Lineage

- Status: Accepted
- Date: 2026-08-19

## Context

Buyer GNB destinations now share one Event Lineage focus path (ADR 0071 /
ADR 0072 / ADR 0073 / ADR 0074). Report-member opens already land Keyman
and evaluation immediately under that next action, ahead of Affiliate
tree (v1.6.0). GNB opens reused the focus flag but did not name the land
order as part of the destination contract.

## Decision

Opening a post from Weekly VOC, Calendar, Customer master, or Ask Agent
lands Keyman and evaluation under the Event Lineage next action, ahead
of Affiliate tree. That is the same order as a report-member open.

A Board home-list open keeps evaluation above Event Lineage and does not
add the Event Lineage next-action copy.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). No
week, CalDAV event, customer, or cited post is invented.

## Consequences

- GNB destination opens and report-member opens share one land contract.
- Closing the popup restores the home-list panel order on the next open.

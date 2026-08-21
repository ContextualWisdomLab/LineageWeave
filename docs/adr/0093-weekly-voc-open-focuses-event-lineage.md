# ADR 0093: Opening a Weekly VOC post focuses Event Lineage

- Status: Accepted
- Date: 2026-08-19

## Context

ADR 0092 names Weekly VOC as an ISO-week list filter and tells the buyer to
open a post to read Event Lineage. Report-member opens already focus the
popup Event Lineage heading. A home-list open must not steal that focus or
add that next-action copy.

## Decision

Opening a Board post while Weekly VOC is active (`voc` only and a concrete
ISO week) is a `fromWeeklyVoc` open. That open reuses the existing Event
Lineage focus path used by report-member opens:

- The popup Event Lineage heading takes focus.
- The popup names the opened post as current in Event Lineage and tells
  the buyer to read Keyman and evaluation next.

A Board open from the unfiltered home list, a reset filter list, or any
path that did not set `fromWeeklyVoc` does not focus Event Lineage and
does not add that copy. Closing the popup clears the Weekly VOC open flag.

No TEPP theta is invented. No cutoff body is invented (ADR 0016).

## Consequences

- Weekly VOC and report-member opens share one focus contract.
- Changing VOC checkboxes or the ISO week so Weekly VOC is no longer
  active makes the next Board open a home-list open.

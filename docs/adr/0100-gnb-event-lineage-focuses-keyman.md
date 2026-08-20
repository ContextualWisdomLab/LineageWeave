# ADR 0100: GNB Event Lineage focuses Keyman as the next read

- Status: Accepted
- Date: 2026-08-20

## Context

Opening a Board Weekly VOC post, Calendar commitment, Customer master
related post, or Ask Agent cited post already focuses Event Lineage and
names Keyman and evaluation as the next read (ADR 0093 / ADR 0094 /
ADR 0095 / ADR 0096 / ADR 0097). A linked Event Lineage DAG walk keeps
those originating flags. The named next action was not landable: focus
stayed on Event Lineage, and the report-member auto-land chain then
skipped ahead to Ask.

A Board home-list open must not gain that Keyman focus or copy.

## Decision

A GNB-origin popup (`fromWeeklyVoc`, `fromCalendar`,
`fromCustomerMaster`, `fromAskAgent`) keeps Event Lineage as the current
named node and moves keyboard focus to the Keyman heading after Keyman
rows have settled:

- Event Lineage still names the opened post as current and tells the
  buyer to read Keyman and evaluation next.
- The Keyman heading (`#post-keyman`) takes focus so that next action is
  landable.
- Evaluation remains immediately under that Keyman block.
- The report-member auto-land chain to related nodes and Ask is not
  used for GNB origins. Report-member opens keep that later chain
  (ADR 0016 member path).

A Board home-list open, including a home-list DAG walk, does not focus
Keyman and does not add the Event Lineage next-action copy.

No TEPP theta is invented. No cutoff body is invented (ADR 0016). No
cited post, customer, week, or CalDAV event is invented.

## Consequences

- GNB destinations share one Keyman-focus contract across the first open
  and a linked DAG walk from that popup.
- Closing the popup still clears the originating flags.

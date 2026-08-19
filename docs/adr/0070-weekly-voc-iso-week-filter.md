# ADR 0070: Weekly VOC is an ISO-8601 week list filter

- Status: Accepted
- Date: 2026-08-19

## Context

Board already exposes checkbox VOC-type filters (ADR 0060). Buyers still need
one named control that shows this week's Voice of Customer posts without
inventing a measurement or collapsing other VOC types into a guessed default.
PR #259 stacked a `<select>` week filter on a stale Board that used a single
string type filter; current Board keeps `typeFilter` as `string[]`.

## Decision

Weekly VOC is a Board list filter, not a report and not ADR 0051 named hints.

- The **Weekly VOC** control sets VOC type to `voc` only and selects the
  latest ISO-8601 week (`YYYY-Www`) present among authorized Voice of
  Customer posts.
- Week membership uses the UTC date of `created_at`. Thursday decides the
  ISO week-year (ISO 8601 week date).
- An explicit ISO-week `<select>` remains available beside the named
  control. Reset filters returns both the checkboxes and the week to All.
- The Board names the next action: Voice of Customer posts for that week
  are current; open a post to read Event Lineage.
- No TEPP theta is invented. No cutoff body is invented (ADR 0016).

## Consequences

- Weekly VOC composes with the existing checkbox VOC vocabulary instead of
  replacing it.
- Posts whose `created_at` cannot be parsed contribute no week and cannot
  be selected by this filter.
- Home-list and Customer-master opens are unchanged until ADR 0071.

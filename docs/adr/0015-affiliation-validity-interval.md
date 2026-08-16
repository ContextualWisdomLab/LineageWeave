# ADR-0015: Affiliation validity interval (proposed)

- Status: Proposed
- Date: 2026-08-16

## Context

`person_affiliation` is N:N with no interval. Compact related-node
chips (ADR-0014) count every stored identity. That is correct for
Priya Nair's two current counterparty orgs after `make seed`. It is
wrong for a person who left one organization last year and now has
exactly one current membership: the chip would still say
`multiple organizations`.

Browne et al. (2001) treat multiple membership as simultaneous
classification. Singer and Willett (2003) treat change over time as
a different structure. Collapsing those two into one unordered set
repeats the same atomistic mistake ADR-0014 already refused for
"primary" org.

Migration numbers `0012+` are reserved on other open heads
(Milestone 2.1 analysis-run registry, #74 ontology stack). This
decision must not steal those numbers.

## Decision (when those heads land)

Add nullable `affiliation_started_on` and `affiliation_ended_on`
(date) on `person_affiliation`. Both null means current and
unbounded. Compact summaries count an identity only when the
as-of date is inside that interval. Seed a synthetic person with
one current org and one ended org; the chip must name the current
org, not `multiple organizations`.

Until then, do not invent interval columns on a second caption PR.

## Consequences

Buyers walking "as of today" will stop seeing leftover orgs as
plural membership. The Keyman list can still show ended rows with
their dates. Full as-of graph walks stay a later change.

## References

See [RELATED_NODE_AFFILIATION_REFERENCES.md](../doctoring/RELATED_NODE_AFFILIATION_REFERENCES.md).

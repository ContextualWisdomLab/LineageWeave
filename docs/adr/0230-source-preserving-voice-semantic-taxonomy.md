# ADR 0230: Source-preserving voice semantic taxonomy

- Status: Accepted
- Date: 2026-08-26

## Context

The imported `source_post.voc_type_code` is provenance, not permission to
overwrite the source or collapse organization relationships into one post
label. Two vocabularies already exist: post types `voc`, `vocc`, `voco`, `vom`,
and `vop`; and post-scoped organization relationships `rel_voc`, `rel_vocc`,
`rel_voco`, `rel_vom`, `rel_vop`, and `rel_vos`. Internal `rel_vos` means Voice
of Supplier. It is not ISO 16355's Voice of Stakeholder and is not in the post
type scheme.

## Decision

Source assertions and contextual-orchestrator-derived assertions are append-only
and separate. Derived assertions require an exact source span, source revision
digest, evidence digest, model receipt, and optional validity interval. A post
or organization may have multiple simultaneous memberships. Conflicting
source and derived concept sets remain disagreement evidence; matching
multi-membership sets are agreement, not a pairwise mismatch. A summary admits
an assertion only while its optional validity interval contains the query
instant. Imported source labels have no business-event validity interval: they
are available as provenance as soon as recorded, even when the post describes
a future event. Optional validity intervals describe derived or explicitly
time-scoped relationship claims, not ingestion availability. No threshold,
weight, keyword, alias rule, or forced winner is permitted. A replacement or
retraction names the superseded assertion and closes validity with provenance.
The database reconciles the source assertion in the same transaction that
inserts or changes `source_post.voc_type_code` or its revision-bearing body.
It retains the prior assertion as a closed, superseded version; migration
replay is a recovery/backfill path, not the normal ingestion lifecycle. The
initial historical backfill records `0230_voice_source_assertion_backfill` in
`data_migration_completion` only after its insert and repair finish in one
transaction. An interrupted run therefore retries, while a completed replay
does not repeatedly hash the source corpus; subsequent writes remain covered
by the trigger.

Counts use the same authorized eligible-post denominator at the same cutoff and
filters. They report source, derived, multi-membership, disagreement, and
unavailable counts. Per-category membership percentages divide by all eligible
posts and disclose that overlapping category counts may exceed the denominator.
Organization-relationship counts use a separately named evidence-bearing
post-by-organization denominator. Filters may narrow period, corporate entity,
PU, team, person, product, or project without changing these denominators.

SHACL excludes `rel_vos` from the post scheme, admits it only in the organization
relationship scheme, and requires derived evidence/digest/receipt/time fields.
Raw `source_post.voc_type_code` is never updated by this projection.

## Consequences

- Operators can compare original and derived semantics without losing either.
- Category totals are intentionally non-additive under multi-membership.
- A missing orchestrator result remains unavailable, never a negative class.
- Product-scoped supplier/customer transitions can coexist across intervals.

## References

International Organization for Standardization. (2017). *ISO 16355-4:2017:
Applications of statistical and related methods to new technology and product
development process—Part 4: Analysis of non-quantitative and quantitative Voice
of Customer and Voice of Stakeholder*. https://www.iso.org/standard/62607.html

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

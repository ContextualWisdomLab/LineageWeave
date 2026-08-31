# ADR 0276: Digest-bound project-journey temporal evidence

- Status: Accepted on this stacked branch; not protected-main truth until merge
- Date: 2026-08-28
- Depends on: ADR 0132, ADR 0231, ADR 0243; TEPP PR #291
- Figma file ID: `SBpgot7uTvMxEaxUwvoc0S`

## Context

TEPP PR #291 publishes canonical JSON and GraphML for bounded Allen interval-
consistency results. The artifact binds a run, snapshot, exact input digest,
ordered event pair, observed/derived status, and supporting assertion ordinals.
It deliberately does not claim that temporal order is a causal transition,
project predecessor, or business-process branch.

LineageWeave already admits related predecessor paths through authorized
`post_lineage_edge` evidence. Promoting every temporally ordered pair to a
project journey would contradict PRD-FR-5E and ADR 0243.

## Decision

LineageWeave accepts only canonical artifact bytes whose SHA-256, run,
snapshot, and exact input digest match caller-computed expected values. The
remote run must also match a persisted terminal TEPP result. Metadata,
relations, elementary Allen kinds, and support ordinals persist in normalized
tables.

Every admitted temporal pair must already be an exact `post_lineage_edge`.
The database foreign key enforces that boundary. Temporal evidence may
corroborate the time order of an existing related-history path; it never
creates a predecessor, branch, responsibility handoff, or causal transition.
A branch is visible only when the independently admitted lineage graph already
contains that topology. A transition still requires its separately governed
observed business or responsibility evidence.

The Project History API attaches the newest immutable temporal evidence whose
analysis cutoff does not exceed the requested view cutoff to the corresponding
visible edge after ABAC selects both endpoints. The customer UI says what the user can do next—open the supporting
records and compare dates—and never names the calculation module.

GraphML is an equivalent provider export, not the ingestion authority. The
canonical typed JSON is the sole admitted payload so two representations
cannot diverge inside the database.

## Consequences

- Exact temporal consistency becomes durable and auditable without duplicating
  mathematical reasoning in Python.
- A valid artifact containing a pair absent from Event Lineage fails closed at
  the foreign-key boundary and rolls back its transaction.
- A future contract that explicitly carries business predecessor or transition
  semantics requires a new ADR; this artifact cannot be reinterpreted later.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

# ADR 0128: Source-grounded quantitative observations

- Status: Accepted
- Date: 2026-08-21

## Context

The summary projection preserves some evidence as free text, but a budget,
capacity, or counted asset cannot be reliably searched or displayed as an
independent semantic fact from that text alone. Numeric normalization must
also preserve what the source actually said: units, qualifiers, and the exact
supporting phrase.

## Decision

Store each source-grounded quantitative fact as one
`post_summary_quantitative_observation` row linked to its post. A row keeps:

- a controlled measurement type and unit;
- the normalized numeric value, and an optional counted quantity such as
  `2 tractors`;
- the source label, raw value text, qualifier text, and exact evidence text;
- the ontology IRI and extraction method.

The contextual orchestrator must return these observations as part of the
summary semantic contract. The application does not create observations by a
local regex or by guessing from a filing timestamp. Missing orchestrator
output remains unavailable, while an existing stale summary remains clearly
stale. The source phrase remains the reader-facing evidence and the numeric
value is a search/filter projection, not a newly inferred business fact.

The post list search and post detail API read the same normalized projection.
The ontology describes the observation class and controlled measurement/unit
terms, but observations are not promoted to a new polymorphic knowledge-graph
node until a graph edge contract is needed.

## Consequences

One fact with two capacities is represented by two observations, while the
count of each asset is retained on its corresponding capacity observation.
Regenerating a summary replaces the post-owned observation rows atomically
with the other summary projections.

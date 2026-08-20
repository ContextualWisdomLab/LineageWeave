# ADR 0100: Persist Event Lineage channel evidence separately from fused rank

- Status: Proposed
- Date: 2026-08-20
- Supersedes: None
- Extends: [ADR 0064](0064-lineage-evidence-and-tree-assembly.md)

## Context

The reconstruction kernel evaluates candidate parent→child links through
independent temporal, secondary-key, text, and optional LLM channels. It then
selects an edge using a weighted fused score. Until this decision, the product
persisted and returned only `post_lineage_edge.fused_score`.

A fused score is useful for ranking, but it is not enough for a buyer to judge
why a connection was selected. It also hides the difference between an
unavailable channel and a channel that actually returned zero. That ambiguity
violates ADR 0064's requirement to keep uncertainty-bearing evidence and makes
an optional LLM channel look more authoritative or more complete than it was.

## Decision

1. Keep `post_lineage_edge` as the selected reconstructed edge and its fused
   ranking value.
2. Persist each available channel result in the normalized child table
   `lineage_edge_channel_score`, keyed by parent, child, and a controlled
   `lineage_channel` lookup code.
3. Do not store channel evidence as JSON or add one nullable column per
   channel. New channels require an explicit reviewed lookup value and
   application mapping.
4. Validate channel names and require finite scores in `[0, 1]` before
   replacing the persisted edge set. Unknown or invalid evidence fails closed.
5. Treat a missing row as **unavailable**, never as zero. In particular, do not
   invent an LLM score when no adjudication channel ran.
6. Return channel scores only after both endpoint posts pass the existing ABAC
   visibility boundary. Channel evidence never grants access by itself.
7. Render the exact fused and channel values in both the SVG edge description
   and an accessible table. The customer-facing next action is to review the
   evidence before relying on the reconstructed connection.
8. Keep truth families separate: reconstruction evidence is inferred lineage,
   not causal fact, public-web verification, TEPP measurement, or fast-mlsirm
   latent measurement.

## Alternatives considered

### Keep only the fused score

Rejected because it prevents meaningful review and cannot distinguish missing
channels from negative evidence.

### Store channel scores in JSON on `post_lineage_edge`

Rejected because the controlled vocabulary, range checks, joins, evolution,
and per-channel auditability become weaker and less portable.

### Add one column per channel

Rejected because optional and future channels would require repeated parent
schema changes and encourage consumers to interpret nullable values
inconsistently.

### Recompute channels on every read

Rejected because model/provider availability, source revisions, and algorithm
versions can change. The Buyer surface must explain the exact evidence used
when the edge was persisted.

## Consequences

- Buyers can inspect why a link exists and recognize when an LLM channel was
  absent.
- The database remains third-normal-form and the parent edge stays compact.
- Rebuilds atomically replace selected edges and their cascading channel rows.
- Consumers must handle an empty channel map without converting absence to
  zero.
- This change does not calibrate the heuristic scores or make them comparable
  to psychometric estimates; fused and channel scores remain product-level
  reconstruction evidence.

## Acceptance evidence

- Real migration and rollback scripts for the normalized table and controlled
  vocabulary.
- RED→GREEN persistence tests covering every channel, unknown-channel failure,
  and range failure.
- ABAC-filtered API projection tests proving absent LLM evidence remains absent.
- Accessible frontend tests for exact values, unavailable evidence, and SVG
  descriptions.
- Full Python, PostgreSQL, frontend, Storybook, security, coverage, package,
  and provenance gates on the final exact head.

## References

Allan, J. (Ed.). (2002). *Topic detection and tracking: Event-based information
organization*. Springer. https://doi.org/10.1007/978-1-4615-0933-2

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal
of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

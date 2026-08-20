# ADR 0101: Persist Event Lineage channel evidence separately from fused rank

- Status: Proposed
- Date: 2026-08-20
- Supersedes: None
- Extends: [ADR 0064](0064-lineage-evidence-and-tree-assembly.md)

## Context

The reconstruction kernel evaluates candidate parent→child links through
independent temporal, secondary-key, text, and optional LLM channels. RankWeave
then selects an edge using a normalized weighted convex score. Before this
decision, the product persisted and returned only
`post_lineage_edge.fused_score`.

A fused score is useful for ranking, but it cannot answer which signals
participated, which signal dominated, what normalized weights were actually
used, or whether an optional channel was unavailable rather than zero. The
meaning can also drift after an algorithm or weight change unless the exact
reconstruction version and generated-at time stay attached to the historic
edge. Those ambiguities violate ADR 0064's uncertainty-bearing evidence
boundary.

## Decision

1. Keep `post_lineage_edge` as the selected reconstructed edge and fused
   ranking value.
2. Create one `lineage_reconstruction_run` per explicit rebuild, carrying a
   stable reconstruction-version identifier and UTC generated-at time.
3. Persist the normalized active profile in
   `lineage_reconstruction_run_channel`. The profile contains only channels
   that actually participated; its positive weights must sum to 1 within an
   explicit application tolerance of `1e-9`.
4. Persist each selected edge's active channel score and exact
   `score × normalized_weight` contribution in the normalized child table
   `lineage_edge_channel_score`.
5. Require contribution totals to reconcile to the persisted fused score within
   the same `1e-9` tolerance before the first database write and again on the
   Buyer read path. Unknown, non-finite, out-of-range, mismatched, or
   non-reconciling evidence fails closed.
6. Do not store channel evidence as JSON or add one nullable column per
   channel. New channels require an explicit controlled lookup value and
   reviewed application mapping.
7. Treat a missing profile or score row as **unavailable**, never as zero. In
   particular, do not invent an LLM score when no adjudication channel ran.
8. Replace the selected graph, score children, run profile, and run metadata in
   one caller-owned transaction. Cascades remove stale score rows, and the
   writer removes superseded run profiles that no surviving edge references.
9. Return evidence only after both endpoint posts pass the existing ABAC
   visibility boundary. Evidence rows never grant access by themselves.
10. Return a deterministic Buyer collection ordered by contribution descending,
    then controlled signal order. Each item carries signal code, localized
    label key, score, weight, contribution, and rank.
11. Render exact values in the SVG description and a keyboard/screen-reader
    accessible disclosure table. Preserve the same values in print and state
    plainly that the connection is inferred evidence, not a causal fact.
12. Keep truth families separate: reconstruction evidence is neither
    public-web verification nor TEPP/fast-mlsirm measurement, and it does not
    become authoritative source truth.

## Alternatives considered

### Keep only the fused score

Rejected because it prevents meaningful review and cannot distinguish missing
channels from negative evidence.

### Store channel scores and weights in JSON on `post_lineage_edge`

Rejected because controlled vocabulary enforcement, range checks, versioned
profiles, joins, and per-signal auditability become weaker and less portable.

### Add one column per channel

Rejected because optional and future channels would require repeated parent
schema changes and encourage consumers to interpret nullable values
inconsistently.

### Recompute weights and contributions on every read

Rejected because model availability, configured weights, source revisions, and
algorithm versions can change. The Buyer surface must explain the exact
historic run rather than a later reinterpretation.

### Retain every superseded reconstruction run indefinitely

Rejected for this current-state graph contract. A new rebuild atomically
supersedes the previous graph, so unreferenced run/profile rows are stale rather
than historical evidence. A future immutable history product must define a
separate retained-run and edge-versioning contract before preserving them.

## Consequences

- Buyers can inspect why a link exists, identify the dominant signal, and see
  when no LLM participated.
- PostgreSQL remains third-normal-form while the selected edge stays compact.
- Duplicate rebuild delivery replaces rather than duplicates the current graph
  and removes orphan score/profile evidence.
- Existing edges created before migration 0053 may have no run metadata; they
  remain explicitly unavailable until an intentional rebuild and are never
  silently reinterpreted.
- Heuristic scores remain uncalibrated reconstruction evidence and are not
  comparable to psychometric estimates.

## Acceptance evidence

- Clean-install, repeated-apply, constraint, and rollback rehearsals against a
  real PostgreSQL database.
- RED→GREEN tests for four-channel and no-LLM profiles, contribution
  reconciliation, fail-before-write validation, and superseded-run cleanup.
- ABAC-filtered API tests for bounded endpoint evidence, deterministic ranking,
  version/time metadata, and absent LLM evidence.
- Accessible, localized frontend tests for exact values, directionality,
  non-causal copy, no-LLM copy, SVG parity, responsive disclosure, and print.
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

# ADR 0169 — Global Ask merges cited lineage from one fetch pair

**Decision status:** Accepted
**Date:** 2026-08-24
**Related:** [0151](0151-ask-multi-lineage-graph.md), [0090](0090-global-ask-lineage-timeline-expansion.md), issue [#568](https://github.com/ContextualWisdomLab/LineageWeave/issues/568)

## Context

ADR 0151 merges every cited post's reconstructed thread into one
`LineageGraph` so Ask can reuse `LineageDag`. The first implementation
called `visible_lineage_graph` once per citation. Each call re-read
every eligible `source_post` row and the full `post_lineage_edge`
table. Focus mode also returned the entire connected component with
`truncated: false`, so a cited post inside a large component could
inflate the Ask payload without naming a bound.

## Decision

1. `lineage_graphs_for_posts` loads visible posts and lineage edges
   once, partitions connected components in memory, and slices the
   per-citation subgraphs from that pair of reads.
2. The merged payload uses the same node bound as the landing
   viewport (`_LINEAGE_GRAPH_NODE_LIMIT` = 500). Cited posts stay
   first. Remaining component nodes follow newest-first. Nodes beyond
   the bound are omitted and `truncated` is true.
3. Isolated cited posts still appear. Analysis-run knowledge cutoff
   and leftover pairs are unchanged. Do not invent a theta.

## Considered alternatives

- Keep the per-citation refetch because the citation cap is 8:
  rejected. The cost is the table scan, not the citation count, and
  the uncapped component is independent of that cap.
- Depth-from-citation hop limit instead of a node cap: deferred. A
  hop limit can hide a cited thread's own branch point; the node cap
  keeps cited posts visible and names the bound.

## Consequences

- N citations issue one `source_post` query and one
  `post_lineage_edge` query.
- A large connected component no longer ships unbounded into Ask.
  Open a cited post to read the full focused thread.

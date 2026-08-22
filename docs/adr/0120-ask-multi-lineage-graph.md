# ADR 0120: Global Ask renders every cited thread as its own branch graph

- Status: Accepted
- Date: 2026-08-22
- Related: [0090](0090-global-ask-lineage-timeline-expansion.md), [0064](0064-lineage-evidence-and-tree-assembly.md)

## Context

ADR 0090 expands only the single top-ranked match through its direct
`post_lineage_edge` neighbors, so an answer could speak to at most one
connected timeline. A Global Ask answer frequently cites posts from more
than one unrelated reconstruct thread -- two separate customer complaints
that happen to share a keyword, for example -- and before this decision
the reader had no way to see how (or whether) those threads relate to each
other; the answer's text evidence facts named a lineage relationship in
prose only for the single expanded anchor.

Separately, `LineageDag`/`layoutLineageDag` (the post-detail popup's Event
Lineage visualization) already renders one `LineageGraph` payload as N
independent branch-tree `<figure>`s, one per reconstruct thread (bucketed
by `LineageGraphNode.group`, `lineageLayout.ts`'s `layoutLineageDag`).
Each thread's own tree is laid out with git-log-style branch/merge
semantics (`is_root`, `is_branch_point`) already -- there was no missing
git-branch-style layout to build, only missing graph *data* for Global
Ask to feed that existing component.

## Decision

`lineage_graphs_for_posts` (`backend/app/lineage_ingestion.py`) merges
every cited post's full reconstructed thread into one `LineageGraph`
payload: it calls the existing, ABAC-checked `visible_lineage_graph` once
per cited post id and deduplicates nodes/edges shared across citations.
`POST /api/ask` returns this as a new `lineage_graph` response field.
`AskAgentPanel` renders `<LineageDag>` under the answer whenever that
field carries nodes -- reusing the post-detail popup's exact rendering
component, so citing posts from two unrelated threads produces two
independent branch-tree figures with no new frontend layout code.

## Considered alternatives

- Build a new, Ask-specific multi-graph component: rejected --
  `LineageDag` already does exactly this (grouped, branch-aware, per-thread
  figures); a second implementation would only risk drifting from the
  post-detail popup's established visual language and accessibility
  behavior for the same underlying data shape.
- Bound the merged graph to the single top-cited post's thread, matching
  ADR 0090's scope: rejected -- that reintroduces the original gap this
  decision addresses (a multi-thread answer showing only one thread).

## Consequences

- An Ask answer's lineage evidence is now visually traceable per cited
  thread, not summarized as prose for one anchor post only.
- `lineage_graphs_for_posts` issues one `visible_lineage_graph` call per
  cited post (each a bounded `source_post` scan plus a full
  `post_lineage_edge` table read); acceptable at the current citation cap
  (`_POST_CHAT_SOURCE_LIMIT` = 8) and the existing `visible_lineage_graph`
  precedent for the post-detail popup, revisit with a single batched query
  if the citation cap grows materially.
- The response payload grows by one field (`lineage_graph`); existing
  consumers that ignore unknown fields are unaffected.

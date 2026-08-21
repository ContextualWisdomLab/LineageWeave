# ADR 0078: Focus the lineage graph on the opened post

- Status: Accepted
- Date: 2026-08-20

## Context

The landing board uses a bounded, newest-first lineage projection so the
browser does not load the entire corpus. That projection can omit the post a
user opens, or one of its related posts. Rendering that global projection in a
post popup therefore makes a real lineage look empty or incomplete.

## Decision

`GET /api/lineage` keeps the bounded landing projection when no `post_id` is
provided. When `post_id` is provided, the backend first applies the normal
source-post eligibility and ABAC checks, then traverses the undirected
connected component of that visible post through `post_lineage_edge` and
returns the component without the landing limit. An isolated or inaccessible
post returns an empty graph, not a fabricated node or a global fallback.

The frontend requests the focused graph when a post is selected and keeps the
global graph only as the initial loading fallback. The graph is an
interaction-time projection; it does not alter stored lineage edges or
analysis-run snapshots.

## Consequences

- Opening a related post shows all visible nodes in its connected lineage
  component, even when those nodes are outside the landing page limit.
- The landing page remains bounded and fast.
- A post with no lineage edge is represented by the existing "no related
  lineage" state rather than an unrelated DAG.
- A focused component can be larger than the landing limit, so the endpoint
  remains authenticated and ABAC-filtered.

## Alternatives rejected

- Increasing the global limit: still fails for older or sparse components and
  increases every landing-page response.
- Returning the selected post as a synthetic singleton node: hides the fact
  that no lineage edge exists and creates misleading graph evidence.
- Loading the entire corpus in the browser: violates the bounded projection
  contract.

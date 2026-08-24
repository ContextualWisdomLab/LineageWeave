# ADR 0195: Persist reconstruct()'s per-channel score breakdown

- Status: Accepted
- Date: 2026-08-24

## Context

While measuring the real-corpus scope of the temporal-floor calibration
gap flagged in ADR 0190 (`docs/product-technical-gap-baseline.md`), a
direct query against `post_lineage_edge` found 148 of 41,257 persisted
edges (0.36%) within one difflib coincidence of
`reconstruct.DEFAULT_MIN_FUSED_SCORE`. Confirming *why* any one of those
148 edges actually formed -- which channel(s) contributed, and how much --
was impossible from the persisted data alone:
`lineageweave.models.Edge.channel_scores` is computed on every
reconstruction (`_best_parent`, `lineageweave/reconstruct.py`) but
`persist_lineage_edges` (`backend/app/lineage_ingestion.py`) has always
discarded it, writing only `parent_post_id`, `child_post_id`, and
`fused_score`. The only way to answer "why did this edge form" was to
re-run reconstruction offline against a source snapshot from the same
point in time -- assuming that snapshot was even still reconstructible.

## Decision

- `migrations/0195_post_lineage_edge_channel_scores.sql` adds a nullable
  `channel_scores jsonb` column to `post_lineage_edge`. Nullable so
  existing rows stay valid; a missing breakdown means "this edge predates
  the column," never a fabricated score (same rule ADR 0064 already
  applies to a missing channel during fusion itself).
- `persist_lineage_edges` now writes `json.dumps(edge.channel_scores, ...)`
  alongside `fused_score` on every insert, matching the existing
  `$N::jsonb` bind pattern already used elsewhere in this codebase
  (`backend/app/analysis_run_start.py`'s TEPP result persistence).
  `scripts/seed_demo_data.py`'s parallel psycopg2 insert path does the
  same with `%s::jsonb`.
- No API or frontend surface is added in this ADR -- this is a pure
  diagnosability addition for direct database inspection (as already used
  once, to produce the ADR 0190 corpus measurement). Exposing the
  breakdown through `GET /api/lineage` or an operator UI is separate,
  deliberately-not-yet-decided product work.

## Consequences

- Any future investigation into why a specific Event Lineage edge formed
  -- like the one that produced this ADR -- can query
  `channel_scores ->> 'text'` etc. directly instead of reconstructing the
  answer by hand from `source_post` timestamps and titles.
- A corpus-wide rebuild (`POST /api/lineage/rebuild`,
  `scripts/import_postgresql_posts.py`) now writes one additional jsonb
  value per edge; negligible relative to the existing per-edge write cost.
- Edges persisted before this migration report `channel_scores is null`
  -- an honest "unknown," not zero-filled or reconstructed scores.

## References — APA 7th

PostgreSQL Global Development Group. (2026). *JSON types* (PostgreSQL 18
documentation). https://www.postgresql.org/docs/current/datatype-json.html

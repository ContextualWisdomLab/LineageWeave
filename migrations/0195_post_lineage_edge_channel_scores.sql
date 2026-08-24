-- ADR 0195: persist reconstruct()'s per-channel score breakdown on every
-- post_lineage_edge row.
--
-- Edge.channel_scores (lineageweave/models.py) is already computed on
-- every reconstruction but was dropped at persist_lineage_edges
-- (backend/app/lineage_ingestion.py) -- once an edge was written, nothing
-- could tell why it formed (which channel(s) contributed, and how much)
-- without re-running reconstruction offline against a source snapshot.
-- Nullable so existing rows stay valid; a missing breakdown means "edge
-- predates this migration," never a fabricated score.

alter table post_lineage_edge
    add column if not exists channel_scores jsonb;

comment on column post_lineage_edge.channel_scores is
    'Per-channel score breakdown from reconstruct() (temporal, secondary_key, '
    'text, llm when available) for the winning parent choice. Null on edges '
    'persisted before this column existed.';

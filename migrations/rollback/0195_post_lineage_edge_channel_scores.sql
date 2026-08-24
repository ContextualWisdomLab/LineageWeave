-- Reverse migration 0195. Persisted edges stay; only the diagnostic
-- breakdown column is removed.

alter table post_lineage_edge
    drop column if exists channel_scores;

-- Rollback for 0135: remove the unavailable channel-weight persistence
-- contract and the raw grouping provenance columns introduced with it.

drop table if exists lineage_channel_weight;

alter table source_post
    drop column if exists source_secondary_grouping_key,
    drop column if exists source_thread_group_key;

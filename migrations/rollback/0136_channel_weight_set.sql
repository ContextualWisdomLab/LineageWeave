-- Rollback for 0136: keep only the deterministic set and restore the
-- single-set primary key.

delete from lineage_channel_weight
 where channel_set_code <> 'channel_set_deterministic';

alter table lineage_channel_weight
    drop constraint if exists lineage_channel_weight_pkey;

alter table lineage_channel_weight
    drop column if exists channel_set_code;

alter table lineage_channel_weight
    add primary key (channel_code);

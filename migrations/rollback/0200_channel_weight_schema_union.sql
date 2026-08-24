-- Rollback of 0200: restore main's 0135 single-set shape. Non-deterministic
-- sets cannot exist under a (channel_code) primary key, so they are removed.

delete from lineage_channel_weight
 where channel_set_code <> 'channel_set_deterministic';

alter table lineage_channel_weight
    drop constraint if exists lineage_channel_set_code_check;
alter table lineage_channel_weight
    drop constraint if exists lineage_channel_weight_pkey;
alter table lineage_channel_weight
    drop column if exists channel_set_code;
alter table lineage_channel_weight
    add primary key (channel_code);

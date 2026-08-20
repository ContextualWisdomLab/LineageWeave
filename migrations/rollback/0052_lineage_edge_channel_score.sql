begin;

drop table if exists lineage_edge_channel_score;

delete from common_lookup_value
 where lookup_category = 'lineage_channel'
   and lookup_code in (
       'lineage_channel_temporal',
       'lineage_channel_secondary_key',
       'lineage_channel_text',
       'lineage_channel_llm'
   );

commit;

drop table if exists post_lineage_edge_signal;
drop table if exists event_lineage_rebuild_channel;
drop table if exists event_lineage_rebuild;
delete from common_lookup_value
 where lookup_code in (
    'lineage_signal_temporal',
    'lineage_signal_secondary_key',
    'lineage_signal_text',
    'lineage_signal_llm'
 );

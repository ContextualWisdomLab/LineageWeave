alter table post_lineage_edge
    drop column if exists interval_relation_code;

delete from common_lookup_value
 where lookup_category = 'interval_relation';

begin;

do $$
begin
    if to_regclass('public.lineage_edge_channel_score') is not null then
        execute 'drop trigger if exists '
            'lineage_edge_channel_contribution_validate '
            'on lineage_edge_channel_score';
    end if;
end
$$;

drop table if exists lineage_edge_channel_score;
drop function if exists validate_lineage_edge_channel_contribution();

drop index if exists post_lineage_edge_reconstruction_run_idx;
alter table post_lineage_edge
    drop constraint if exists post_lineage_edge_reconstruction_run_fk;
alter table post_lineage_edge
    drop column if exists lineage_reconstruction_run_id;

drop table if exists lineage_reconstruction_run_channel;
drop table if exists lineage_reconstruction_run;

delete from common_lookup_value
 where lookup_category = 'lineage_channel'
   and lookup_code in (
       'lineage_channel_temporal',
       'lineage_channel_secondary_key',
       'lineage_channel_text',
       'lineage_channel_llm'
   );

commit;

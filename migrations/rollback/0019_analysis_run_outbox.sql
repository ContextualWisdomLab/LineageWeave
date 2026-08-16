-- Fail-closed rollback for migration 0019.
--
-- Delivery evidence must be empty before these objects can be removed.
-- Re-running this rollback after a successful empty rollback is safe.

begin;

do $$
declare
    relation_name text;
    relation_has_rows boolean;
begin
    foreach relation_name in array array[
        'analysis_run_lineage_edge',
        'analysis_run_outbox'
    ] loop
        if to_regclass('public.' || relation_name) is not null then
            execute format('select exists (select 1 from %I)', relation_name)
               into relation_has_rows;
            if relation_has_rows then
                raise exception 'analysis_run_outbox_not_empty';
            end if;
        end if;
    end loop;
end
$$;

drop trigger if exists analysis_run_lineage_edge_update_guard
    on analysis_run_lineage_edge;
drop function if exists reject_analysis_run_lineage_edge_mutation();
drop table if exists analysis_run_lineage_edge;
drop table if exists analysis_run_outbox;

delete from common_lookup_value
 where lookup_code in (
    'analysis_delivery_lineage',
    'analysis_delivery_queued',
    'analysis_delivery_leased',
    'analysis_delivery_completed',
    'analysis_delivery_failed'
 );

commit;

-- Fail-closed rollback for migration 0012.
--
-- Registry evidence must be exported or explicitly deleted under an approved
-- retention procedure before these objects can be removed. Re-running this
-- rollback after a successful empty rollback is safe.

begin;

do $$
declare
    relation_name text;
    relation_has_rows boolean;
begin
    foreach relation_name in array array[
        'analysis_run_status_event',
        'analysis_run_scope',
        'analysis_run',
        'analysis_source_count',
        'analysis_source_snapshot'
    ] loop
        if to_regclass('public.' || relation_name) is not null then
            execute format('select exists (select 1 from %I)', relation_name)
               into relation_has_rows;
            if relation_has_rows then
                raise exception 'analysis_run_registry_not_empty';
            end if;
        end if;
    end loop;
end
$$;

drop view if exists analysis_run_current_status;
drop table if exists analysis_run_status_event;
drop table if exists analysis_run_scope;
drop table if exists analysis_run;
drop table if exists analysis_source_count;
drop table if exists analysis_source_snapshot;

drop function if exists enforce_analysis_run_status_transition();
drop function if exists reject_analysis_run_status_mutation();
drop function if exists reject_analysis_run_scope_mutation();
drop function if exists reject_analysis_run_mutation();
drop function if exists reject_analysis_run_update();
drop function if exists enforce_analysis_run_knowledge_cutoff();
drop function if exists enforce_analysis_source_count_freeze();
drop function if exists reject_analysis_source_count_update();
drop function if exists reject_analysis_source_snapshot_update();

delete from common_lookup_value
 where lookup_code in (
    'analysis_run_lineage',
    'analysis_run_report',
    'analysis_run_tepp',
    'analysis_status_pending',
    'analysis_status_running',
    'analysis_status_succeeded',
    'analysis_status_failed',
    'analysis_status_cancelled',
    'analysis_scope_all_visible',
    'analysis_scope_corporate_entity',
    'analysis_scope_process_unit',
    'analysis_scope_thread_group',
    'analysis_count_source_row',
    'analysis_count_document',
    'analysis_count_thread',
    'analysis_count_lineage_node',
    'analysis_count_lineage_edge'
 );

commit;

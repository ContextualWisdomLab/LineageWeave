-- Fail-closed rollback for the normalized analysis-run registry.
--
-- The rollback is intentionally idempotent, but it refuses to erase any
-- persisted provenance. Operators must export required evidence and explicitly
-- clear the registry under an approved maintenance procedure before downgrade.

begin;

do $$
begin
    if to_regclass('public.analysis_run_status_event') is not null
       and exists (select 1 from analysis_run_status_event limit 1) then
        raise exception 'analysis_run_registry_not_empty';
    end if;
    if to_regclass('public.analysis_run_scope') is not null
       and exists (select 1 from analysis_run_scope limit 1) then
        raise exception 'analysis_run_registry_not_empty';
    end if;
    if to_regclass('public.analysis_run') is not null
       and exists (select 1 from analysis_run limit 1) then
        raise exception 'analysis_run_registry_not_empty';
    end if;
    if to_regclass('public.analysis_source_count') is not null
       and exists (select 1 from analysis_source_count limit 1) then
        raise exception 'analysis_run_registry_not_empty';
    end if;
    if to_regclass('public.analysis_source_snapshot') is not null
       and exists (select 1 from analysis_source_snapshot limit 1) then
        raise exception 'analysis_run_registry_not_empty';
    end if;
end
$$;

drop view if exists analysis_run_current_status;

drop table if exists analysis_run_status_event;
drop table if exists analysis_run_scope;
drop table if exists analysis_run;
drop table if exists analysis_source_count;
drop table if exists analysis_source_snapshot;

drop function if exists reject_analysis_run_status_event_mutation();
drop function if exists enforce_analysis_run_status_transition();
drop function if exists enforce_analysis_source_count_freeze();
drop function if exists reject_analysis_run_mutation();
drop function if exists enforce_analysis_run_knowledge_cutoff();
drop function if exists reject_analysis_source_count_update();
drop function if exists reject_analysis_source_snapshot_update();

do $$
begin
    if to_regclass('public.common_lookup_value') is not null then
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
    end if;
end
$$;

commit;

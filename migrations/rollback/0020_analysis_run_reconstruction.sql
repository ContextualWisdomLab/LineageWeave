-- Fail-closed rollback for migration 0020.
--
-- Reconstruction evidence must be exported or explicitly deleted under an
-- approved retention procedure before these objects can be removed.

begin;

do $$
declare
    relation_name text;
    relation_has_rows boolean;
begin
    foreach relation_name in array array[
        'analysis_run_lineage_edge',
        'analysis_run_reconstruction'
    ] loop
        if to_regclass('public.' || relation_name) is not null then
            execute format('select exists (select 1 from %I)', relation_name)
               into relation_has_rows;
            if relation_has_rows then
                raise exception 'analysis_run_reconstruction_not_empty';
            end if;
        end if;
    end loop;
end
$$;

drop trigger if exists analysis_run_lineage_edge_update_reject
    on analysis_run_lineage_edge;
drop trigger if exists analysis_run_reconstruction_update_reject
    on analysis_run_reconstruction;
drop function if exists reject_analysis_run_lineage_edge_update();
drop function if exists reject_analysis_run_reconstruction_update();
drop table if exists analysis_run_lineage_edge;
drop table if exists analysis_run_reconstruction;

commit;

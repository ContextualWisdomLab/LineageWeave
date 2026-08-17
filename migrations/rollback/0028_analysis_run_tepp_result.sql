-- Fail-closed rollback for migration 0028.
--
-- Persistable TEPP results must be exported or explicitly deleted under an
-- approved retention procedure before these objects can be removed.

begin;

do $$
declare
    relation_has_rows boolean;
begin
    if to_regclass('public.analysis_run_tepp_result') is not null then
        execute 'select exists (select 1 from analysis_run_tepp_result)'
           into relation_has_rows;
        if relation_has_rows then
            raise exception 'analysis_run_tepp_result_not_empty';
        end if;
    end if;
end
$$;

drop trigger if exists analysis_run_tepp_result_update_reject
    on analysis_run_tepp_result;
drop function if exists reject_analysis_run_tepp_result_update();
drop table if exists analysis_run_tepp_result;

commit;

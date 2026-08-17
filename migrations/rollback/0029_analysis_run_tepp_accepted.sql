-- Fail-closed rollback for migration 0029.
--
-- Accepted TEPP transport evidence must be exported or explicitly deleted
-- under an approved retention procedure before these objects can be removed.
-- This rollback does not drop analysis_run_tepp_result (0028).

begin;

do $$
declare
    relation_has_rows boolean;
begin
    if to_regclass('public.analysis_run_tepp_accepted') is not null then
        execute 'select exists (select 1 from analysis_run_tepp_accepted)'
           into relation_has_rows;
        if relation_has_rows then
            raise exception 'analysis_run_tepp_accepted_not_empty';
        end if;
    end if;
end
$$;

drop trigger if exists analysis_run_tepp_accepted_update_reject
    on analysis_run_tepp_accepted;
drop function if exists reject_analysis_run_tepp_accepted_update();
drop table if exists analysis_run_tepp_accepted;

commit;

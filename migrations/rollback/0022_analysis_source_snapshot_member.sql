-- Fail-closed rollback for migration 0022.
--
-- Snapshot membership must be exported or explicitly deleted under an
-- approved retention procedure before these objects can be removed.

begin;

do $$
declare
    relation_has_rows boolean;
begin
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        execute 'select exists (select 1 from analysis_source_snapshot_member)'
           into relation_has_rows;
        if relation_has_rows then
            raise exception 'analysis_source_snapshot_member_not_empty';
        end if;
    end if;
end
$$;

drop trigger if exists analysis_source_snapshot_member_update_reject
    on analysis_source_snapshot_member;
drop function if exists reject_analysis_source_snapshot_member_update();
drop table if exists analysis_source_snapshot_member;

commit;

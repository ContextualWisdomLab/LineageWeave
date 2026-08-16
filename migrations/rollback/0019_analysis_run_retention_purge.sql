-- Fail-closed rollback for migration 0019.
--
-- Export analysis_run_retention_event, then delete those rows, before
-- this script can drop the purge function and audit table. Re-running
-- after a successful empty rollback is safe.

begin;

do $$
declare
    relation_has_rows boolean;
begin
    if to_regclass('public.analysis_run_retention_event') is not null then
        execute 'select exists (select 1 from analysis_run_retention_event)'
           into relation_has_rows;
        if relation_has_rows then
            raise exception 'analysis_run_retention_event_not_empty';
        end if;
    end if;
end
$$;

drop function if exists purge_analysis_run_registry(text);
drop table if exists analysis_run_retention_event;

-- analysis_run_retention_admin is cluster-scoped. Leave it in place so a
-- parallel database that still has 0019 applied does not lose the role.
-- Revoke leftover memberships before dropping the role in a dedicated
-- cluster teardown.

commit;

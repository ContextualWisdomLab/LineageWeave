-- Restore migration 0018's update-only scope guard.
-- This rollback changes the mutation policy but does not remove registry data.

begin;

drop trigger if exists analysis_run_scope_mutation_reject
    on analysis_run_scope;
drop function if exists reject_analysis_run_scope_mutation();

create or replace function reject_analysis_run_scope_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_scope_is_immutable';
end
$$;

comment on function reject_analysis_run_scope_update() is
    'Rejects mutation of the authorization scope attached to a run.';

create trigger analysis_run_scope_update_reject
before update on analysis_run_scope
for each row execute function reject_analysis_run_scope_update();

commit;

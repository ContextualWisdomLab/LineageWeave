-- Make the authorization scope attached to an analysis run fully immutable.
-- Migration 0018 already rejected scope updates. Deletion would still remove
-- the only persisted authorization boundary while leaving the run and status
-- history intact, so both mutation forms must fail closed.

begin;

drop trigger if exists analysis_run_scope_update_reject
    on analysis_run_scope;
drop trigger if exists analysis_run_scope_mutation_reject
    on analysis_run_scope;

drop function if exists reject_analysis_run_scope_update();

create or replace function reject_analysis_run_scope_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_scope_is_immutable';
end
$$;

comment on function reject_analysis_run_scope_mutation() is
    'Rejects update/delete of an analysis run authorization scope.';

create trigger analysis_run_scope_mutation_reject
before update or delete on analysis_run_scope
for each row execute function reject_analysis_run_scope_mutation();

commit;

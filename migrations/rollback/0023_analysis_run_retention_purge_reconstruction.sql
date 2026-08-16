-- Rollback for migration 0023 restores the 0020 purge body.
--
-- After this script, a granted purge no longer deletes reconstruction
-- or snapshot-member rows. Export and empty those tables with the 0023
-- function before rolling back 0022 and 0021.

begin;

-- Recreate the 0020 function text. Source of truth remains
-- migrations/0020_analysis_run_retention_purge.sql; this copy exists
-- only so 0023 can be reversed without re-running 0020's DDL.

create or replace function purge_analysis_run_registry(approval_token text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    run_count bigint;
    snapshot_count bigint;
begin
    if not exists (
        select 1
        from analysis_run_retention_grant
        where database_role_name = session_user
          and revoked_at is null
    ) then
        raise exception 'analysis_run_retention_not_granted';
    end if;

    if not pg_has_role(session_user, 'analysis_run_retention_admin', 'member') then
        raise exception 'analysis_run_retention_not_admin';
    end if;

    if approval_token is distinct from 'approved-retention-purge' then
        raise exception 'analysis_run_retention_not_approved';
    end if;

    select count(*) into run_count from analysis_run;
    select count(*) into snapshot_count from analysis_source_snapshot;

    alter table analysis_run_status_event
        disable trigger analysis_run_status_event_delete_reject;
    alter table analysis_run_scope
        disable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run
        disable trigger analysis_run_mutation_reject;

    begin
        delete from analysis_run_status_event;
        delete from analysis_run_scope;
        delete from analysis_run;
        delete from analysis_source_count;
        delete from analysis_source_snapshot;
    exception
        when others then
            alter table analysis_run
                enable trigger analysis_run_mutation_reject;
            alter table analysis_run_scope
                enable trigger analysis_run_scope_mutation_reject;
            alter table analysis_run_status_event
                enable trigger analysis_run_status_event_delete_reject;
            raise;
    end;

    alter table analysis_run
        enable trigger analysis_run_mutation_reject;
    alter table analysis_run_scope
        enable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run_status_event
        enable trigger analysis_run_status_event_delete_reject;

    insert into analysis_run_retention_event (
        purged_run_count,
        purged_snapshot_count,
        approval_token_digest,
        invoking_session_role,
        invoking_current_role,
        client_network_address
    ) values (
        run_count,
        snapshot_count,
        encode(sha256(convert_to(approval_token, 'UTF8')), 'hex'),
        session_user,
        current_user,
        inet_client_addr()
    );
end
$$;

comment on function purge_analysis_run_registry(text) is
    'Empties immutable registry relations after an unrevoked role grant, '
    'analysis_run_retention_admin membership, and the documented approval '
    'token; records one analysis_run_retention_event. Next action: export '
    'that event, delete it, then roll back 0020 and 0018.';

revoke all on function purge_analysis_run_registry(text) from public;
grant execute on function purge_analysis_run_registry(text)
    to analysis_run_retention_admin;

commit;

-- Granted purge must empty reconstruction evidence (ADR 0022).
--
-- Landed 0021 / 0022 add immutable reconstruction and snapshot-member
-- rows that reference analysis_run / analysis_source_snapshot. The
-- 0020 purge deleted only the 0018 registry tables, so a granted empty
-- after start failed on foreign keys. Replace the function so the
-- documented operator path still works.
--
-- Authorization stays conjunctive (ADR 0020): unrevoked grant, admin
-- membership, then the published phrase. PUBLIC still has no EXECUTE.

begin;

create or replace function purge_analysis_run_registry(approval_token text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    run_count bigint;
    snapshot_count bigint;
    has_reconstruction boolean;
    has_snapshot_member boolean;
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
    has_reconstruction := to_regclass('public.analysis_run_reconstruction') is not null;
    has_snapshot_member := to_regclass('public.analysis_source_snapshot_member') is not null;

    alter table analysis_run_status_event
        disable trigger analysis_run_status_event_delete_reject;
    alter table analysis_run_scope
        disable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run
        disable trigger analysis_run_mutation_reject;
    if has_reconstruction then
        alter table analysis_run_lineage_edge
            disable trigger analysis_run_lineage_edge_update_reject;
        alter table analysis_run_reconstruction
            disable trigger analysis_run_reconstruction_update_reject;
    end if;
    if has_snapshot_member then
        alter table analysis_source_snapshot_member
            disable trigger analysis_source_snapshot_member_update_reject;
    end if;

    begin
        if has_reconstruction then
            delete from analysis_run_lineage_edge;
            delete from analysis_run_reconstruction;
        end if;
        delete from analysis_run_status_event;
        delete from analysis_run_scope;
        delete from analysis_run;
        delete from analysis_source_count;
        if has_snapshot_member then
            delete from analysis_source_snapshot_member;
        end if;
        delete from analysis_source_snapshot;
    exception
        when others then
            if has_snapshot_member then
                alter table analysis_source_snapshot_member
                    enable trigger analysis_source_snapshot_member_update_reject;
            end if;
            if has_reconstruction then
                alter table analysis_run_reconstruction
                    enable trigger analysis_run_reconstruction_update_reject;
                alter table analysis_run_lineage_edge
                    enable trigger analysis_run_lineage_edge_update_reject;
            end if;
            alter table analysis_run
                enable trigger analysis_run_mutation_reject;
            alter table analysis_run_scope
                enable trigger analysis_run_scope_mutation_reject;
            alter table analysis_run_status_event
                enable trigger analysis_run_status_event_delete_reject;
            raise;
    end;

    if has_snapshot_member then
        alter table analysis_source_snapshot_member
            enable trigger analysis_source_snapshot_member_update_reject;
    end if;
    if has_reconstruction then
        alter table analysis_run_reconstruction
            enable trigger analysis_run_reconstruction_update_reject;
        alter table analysis_run_lineage_edge
            enable trigger analysis_run_lineage_edge_update_reject;
    end if;
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
    'Empties immutable registry, reconstruction, and snapshot-member '
    'relations after an unrevoked role grant, analysis_run_retention_admin '
    'membership, and the documented approval token. Next action: export '
    'analysis_run_retention_event, delete it, then roll back 0023, 0022, '
    '0021, 0020, and 0018.';

revoke all on function purge_analysis_run_registry(text) from public;
grant execute on function purge_analysis_run_registry(text)
    to analysis_run_retention_admin;

commit;

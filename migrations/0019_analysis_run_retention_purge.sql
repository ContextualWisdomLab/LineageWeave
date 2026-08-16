-- Privileged retention purge for the Milestone 2 analysis-run registry.
--
-- Migration 0018 makes analysis_run / scope / status immutable, so a
-- documented "export or delete under an approved retention procedure"
-- cannot empty a run-bearing registry. This slice adds that procedure:
-- an audited SECURITY DEFINER purge that disables the immutability
-- triggers only inside the approved call, then records one retention
-- event. A published token is not enough: the caller must hold an
-- unrevoked analysis_run_retention_grant, and PUBLIC cannot execute
-- the function. A session SET cannot authorize a raw DELETE.

begin;

create table if not exists analysis_run_retention_grant (
    analysis_run_retention_grant_id uuid primary key default gen_random_uuid(),
    database_role_name text not null
        check (char_length(database_role_name) >= 1),
    granted_at timestamptz not null default clock_timestamp(),
    revoked_at timestamptz,
    check (revoked_at is null or revoked_at >= granted_at)
);

comment on table analysis_run_retention_grant is
    'Unrevoked row authorizes session_user to call '
    'purge_analysis_run_registry. Insert one grant for the operator '
    'role before the first purge.';

comment on column analysis_run_retention_grant.database_role_name is
    'PostgreSQL session_user that may purge; not an application account.';

create unique index if not exists analysis_run_retention_grant_active
    on analysis_run_retention_grant (database_role_name)
    where revoked_at is null;

create table if not exists analysis_run_retention_event (
    analysis_run_retention_event_id uuid primary key default gen_random_uuid(),
    approved_at timestamptz not null default clock_timestamp(),
    purged_run_count bigint not null check (purged_run_count >= 0),
    purged_snapshot_count bigint not null check (purged_snapshot_count >= 0),
    approval_token_digest text not null
        check (approval_token_digest ~ '^[0-9a-f]{64}$'),
    invoking_session_role text not null
        check (char_length(invoking_session_role) >= 1)
);

comment on table analysis_run_retention_event is
    'One audit row per approved registry purge; export then delete before '
    'rolling back migration 0019.';

comment on column analysis_run_retention_event.approval_token_digest is
    'SHA-256 hex of the approval token; the raw phrase is never stored.';

comment on column analysis_run_retention_event.invoking_session_role is
    'session_user that held the grant and called the purge; '
    'SECURITY DEFINER current_user is the function owner and is not stored.';

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
        invoking_session_role
    ) values (
        run_count,
        snapshot_count,
        encode(sha256(convert_to(approval_token, 'UTF8')), 'hex'),
        session_user
    );
end
$$;

comment on function purge_analysis_run_registry(text) is
    'Empties immutable registry relations after an unrevoked role grant '
    'and the documented approval token; records one '
    'analysis_run_retention_event. Next action: export that event, '
    'delete it, then roll back 0019 and 0018.';

insert into analysis_run_retention_grant (database_role_name)
select session_user
where not exists (
    select 1
    from analysis_run_retention_grant
    where database_role_name = session_user
      and revoked_at is null
);

revoke all on function purge_analysis_run_registry(text) from public;

commit;

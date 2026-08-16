-- Privileged retention purge for the Milestone 2 analysis-run registry.
--
-- Migration 0018 makes analysis_run / scope / status immutable, so a
-- documented "export or delete under an approved retention procedure"
-- cannot empty a run-bearing registry. This slice adds that procedure:
-- an audited SECURITY DEFINER purge that disables the immutability
-- triggers only inside the approved call, then records one retention
-- event.
--
-- Fail-closed authorization is conjunctive (ADR 0020):
--   1. session_user holds an unrevoked analysis_run_retention_grant;
--   2. session_user is a member of analysis_run_retention_admin;
--   3. the documented approval phrase is supplied.
-- PUBLIC cannot execute the function. The phrase is a procedure name,
-- not an authorization secret. A session SET cannot authorize a raw
-- DELETE. Do not grant the admin role to the application DATABASE_URL
-- login, and do not insert a grant for that login.
--
-- ADR 0019 / migration 0019 belong to the R&R catalog-id bind
-- (cataloged_team_id / cataloged_corporate_entity_id). Do not reuse
-- that number for this purge.

begin;

do $$
begin
    if not exists (
        select 1 from pg_roles where rolname = 'analysis_run_retention_admin'
    ) then
        create role analysis_run_retention_admin nologin nosuperuser inherit;
    end if;
end
$$;

comment on role analysis_run_retention_admin is
    'Least-privilege role that may call purge_analysis_run_registry. '
    'Grant this role to an operator session, then insert an unrevoked '
    'analysis_run_retention_grant for session_user. Do not grant it to '
    'the application DATABASE_URL role.';

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
    'role and grant analysis_run_retention_admin before the first purge.';

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
    invoking_session_role name not null,
    invoking_current_role name not null,
    client_network_address inet
);

comment on table analysis_run_retention_event is
    'One audit row per approved registry purge; export then delete before '
    'rolling back migration 0020.';

comment on column analysis_run_retention_event.approval_token_digest is
    'SHA-256 hex of the approval token; the raw phrase is never stored.';

comment on column analysis_run_retention_event.invoking_session_role is
    'session_user at purge time: the login role that held the grant.';

comment on column analysis_run_retention_event.invoking_current_role is
    'current_user at purge time: the SECURITY DEFINER owner while the '
    'function runs.';

comment on column analysis_run_retention_event.client_network_address is
    'inet_client_addr() when the caller is remote; NULL for local sockets.';

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

    -- ADR 0021 start reconstruction adds immutable children. Those
    -- tables are absent on a 0.87.0-only database. When present, their
    -- delete-reject triggers and FKs would otherwise force a superuser
    -- DISABLE TRIGGER — the failure this procedure exists to remove.
    if to_regclass('public.analysis_run_lineage_edge') is not null then
        execute 'alter table analysis_run_lineage_edge disable trigger user';
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        execute 'alter table analysis_run_reconstruction disable trigger user';
    end if;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        execute 'alter table analysis_source_snapshot_member disable trigger user';
    end if;

    alter table analysis_run_status_event
        disable trigger analysis_run_status_event_delete_reject;
    alter table analysis_run_scope
        disable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run
        disable trigger analysis_run_mutation_reject;

    begin
        if to_regclass('public.analysis_run_lineage_edge') is not null then
            delete from analysis_run_lineage_edge;
        end if;
        if to_regclass('public.analysis_run_reconstruction') is not null then
            delete from analysis_run_reconstruction;
        end if;
        delete from analysis_run_status_event;
        delete from analysis_run_scope;
        delete from analysis_run;
        delete from analysis_source_count;
        if to_regclass('public.analysis_source_snapshot_member') is not null then
            delete from analysis_source_snapshot_member;
        end if;
        delete from analysis_source_snapshot;
    exception
        when others then
            alter table analysis_run
                enable trigger analysis_run_mutation_reject;
            alter table analysis_run_scope
                enable trigger analysis_run_scope_mutation_reject;
            alter table analysis_run_status_event
                enable trigger analysis_run_status_event_delete_reject;
            if to_regclass('public.analysis_source_snapshot_member') is not null then
                execute 'alter table analysis_source_snapshot_member enable trigger user';
            end if;
            if to_regclass('public.analysis_run_reconstruction') is not null then
                execute 'alter table analysis_run_reconstruction enable trigger user';
            end if;
            if to_regclass('public.analysis_run_lineage_edge') is not null then
                execute 'alter table analysis_run_lineage_edge enable trigger user';
            end if;
            raise;
    end;

    alter table analysis_run
        enable trigger analysis_run_mutation_reject;
    alter table analysis_run_scope
        enable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run_status_event
        enable trigger analysis_run_status_event_delete_reject;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        execute 'alter table analysis_source_snapshot_member enable trigger user';
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        execute 'alter table analysis_run_reconstruction enable trigger user';
    end if;
    if to_regclass('public.analysis_run_lineage_edge') is not null then
        execute 'alter table analysis_run_lineage_edge enable trigger user';
    end if;

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
    'token; also empties analysis_run_lineage_edge, '
    'analysis_run_reconstruction, and analysis_source_snapshot_member '
    'when those ADR 0021 relations exist. Next action: export '
    'analysis_run_retention_event, delete it, then roll back 0020 and 0018.';

revoke all on function purge_analysis_run_registry(text) from public;
grant execute on function purge_analysis_run_registry(text)
    to analysis_run_retention_admin;

commit;

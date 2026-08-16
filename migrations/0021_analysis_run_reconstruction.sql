-- Run-scoped lineage reconstruction result (ADR 0021).
--
-- A Pending analysis run may later persist the ThreadWeave parent
-- choices for its cutoff bag. Edges belong to the run, not the live
-- Event Lineage panel. No post body, DSN, or fabricated measurement
-- is stored.
--
-- ADR 0019 is the R&R catalog-id bind. ADR 0020 is the granted
-- retention purge. Do not reuse those numbers.
--
-- This migration also replaces purge_analysis_run_registry so a
-- granted purge deletes reconstruction rows (and snapshot members
-- when migration 0022 is present) before the 0018 registry tables.

begin;

create table if not exists analysis_run_reconstruction (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    result_sha256 text not null,
    edge_count integer not null,
    reconstructed_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    constraint analysis_run_reconstruction_digest_check
        check (result_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_reconstruction_edge_count_check
        check (edge_count >= 0),
    constraint analysis_run_reconstruction_time_check
        check (reconstructed_at <= recorded_at)
);

comment on table analysis_run_reconstruction is
    'One immutable reconstruction digest per analysis run; never a post body '
    'or a fabricated psychometric score.';

create table if not exists analysis_run_lineage_edge (
    analysis_run_id uuid not null
        references analysis_run_reconstruction (analysis_run_id),
    child_post_id uuid not null
        references source_post (post_id),
    parent_post_id uuid not null
        references source_post (post_id),
    fused_score double precision not null,
    reconstructed_at timestamptz not null,
    primary key (analysis_run_id, child_post_id),
    constraint analysis_run_lineage_edge_distinct_check
        check (child_post_id <> parent_post_id),
    constraint analysis_run_lineage_edge_score_check
        check (fused_score >= 0 and fused_score <= 1)
);

comment on table analysis_run_lineage_edge is
    'One reconstructed parent choice per child post inside one analysis run.';

create or replace function reject_analysis_run_reconstruction_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_reconstruction_is_immutable';
end
$$;

comment on function reject_analysis_run_reconstruction_update() is
    'Rejects mutation of a persisted reconstruction digest.';

drop trigger if exists analysis_run_reconstruction_update_reject
    on analysis_run_reconstruction;
create trigger analysis_run_reconstruction_update_reject
before update or delete on analysis_run_reconstruction
for each row execute function reject_analysis_run_reconstruction_update();

create or replace function reject_analysis_run_lineage_edge_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_lineage_edge_is_immutable';
end
$$;

comment on function reject_analysis_run_lineage_edge_update() is
    'Rejects mutation of a persisted run-scoped lineage edge.';

drop trigger if exists analysis_run_lineage_edge_update_reject
    on analysis_run_lineage_edge;
create trigger analysis_run_lineage_edge_update_reject
before update or delete on analysis_run_lineage_edge
for each row execute function reject_analysis_run_lineage_edge_update();

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
    'Empties immutable registry and reconstruction relations after an '
    'unrevoked role grant, analysis_run_retention_admin membership, and '
    'the documented approval token. Next action: export '
    'analysis_run_retention_event, delete it, then roll back 0022, 0021, '
    '0020, and 0018.';

revoke all on function purge_analysis_run_registry(text) from public;
grant execute on function purge_analysis_run_registry(text)
    to analysis_run_retention_admin;

commit;

-- Persistable TEPP measurement result (ADR 0034).
--
-- A live TEPP transport may return a time / multilevel / multi-affiliation
-- result. This table stores those aggregates on the analysis run. It does
-- not store a theta, IRT item parameter, topic, or ALR payload.

create table if not exists analysis_run_tepp_result (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    result_sha256 text not null,
    interval_count integer not null,
    level_count integer not null,
    affiliation_count integer not null,
    measured_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    constraint analysis_run_tepp_result_digest_check
        check (result_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_tepp_result_interval_count_check
        check (interval_count >= 0),
    constraint analysis_run_tepp_result_level_count_check
        check (level_count >= 0),
    constraint analysis_run_tepp_result_affiliation_count_check
        check (affiliation_count >= 0),
    constraint analysis_run_tepp_result_time_check
        check (measured_at <= recorded_at)
);

comment on table analysis_run_tepp_result is
    'One immutable TEPP time / multilevel / multi-affiliation result per '
    'analysis run; never a theta, item bank, topic, or ALR payload.';

create or replace function reject_analysis_run_tepp_result_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_tepp_result_is_immutable';
end
$$;

comment on function reject_analysis_run_tepp_result_update() is
    'Rejects mutation of a persisted TEPP measurement result.';

drop trigger if exists analysis_run_tepp_result_update_reject
    on analysis_run_tepp_result;
create trigger analysis_run_tepp_result_update_reject
before update or delete on analysis_run_tepp_result
for each row execute function reject_analysis_run_tepp_result_update();

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
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox
            disable trigger analysis_run_outbox_mutation_reject;
        alter table analysis_run_outbox_delivery
            disable trigger analysis_run_outbox_delivery_mutation_reject;
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        alter table analysis_run_reconstruction
            disable trigger analysis_run_reconstruction_update_reject;
        alter table analysis_run_lineage_edge
            disable trigger analysis_run_lineage_edge_update_reject;
    end if;
    if to_regclass('public.analysis_run_tepp_result') is not null then
        alter table analysis_run_tepp_result
            disable trigger analysis_run_tepp_result_update_reject;
    end if;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        alter table analysis_source_snapshot_member
            disable trigger analysis_source_snapshot_member_update_reject;
    end if;

    begin
        if to_regclass('public.analysis_run_outbox_delivery') is not null then
            delete from analysis_run_outbox_delivery;
            delete from analysis_run_outbox;
        end if;
        if to_regclass('public.analysis_run_lineage_edge') is not null then
            delete from analysis_run_lineage_edge;
        end if;
        if to_regclass('public.analysis_run_reconstruction') is not null then
            delete from analysis_run_reconstruction;
        end if;
        if to_regclass('public.analysis_run_tepp_result') is not null then
            delete from analysis_run_tepp_result;
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
            if to_regclass('public.analysis_run_outbox') is not null then
                alter table analysis_run_outbox
                    enable trigger analysis_run_outbox_mutation_reject;
                alter table analysis_run_outbox_delivery
                    enable trigger analysis_run_outbox_delivery_mutation_reject;
            end if;
            if to_regclass('public.analysis_run_reconstruction') is not null then
                alter table analysis_run_reconstruction
                    enable trigger analysis_run_reconstruction_update_reject;
                alter table analysis_run_lineage_edge
                    enable trigger analysis_run_lineage_edge_update_reject;
            end if;
            if to_regclass('public.analysis_run_tepp_result') is not null then
                alter table analysis_run_tepp_result
                    enable trigger analysis_run_tepp_result_update_reject;
            end if;
            if to_regclass('public.analysis_source_snapshot_member') is not null then
                alter table analysis_source_snapshot_member
                    enable trigger analysis_source_snapshot_member_update_reject;
            end if;
            raise;
    end;

    alter table analysis_run
        enable trigger analysis_run_mutation_reject;
    alter table analysis_run_scope
        enable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run_status_event
        enable trigger analysis_run_status_event_delete_reject;
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox
            enable trigger analysis_run_outbox_mutation_reject;
        alter table analysis_run_outbox_delivery
            enable trigger analysis_run_outbox_delivery_mutation_reject;
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        alter table analysis_run_reconstruction
            enable trigger analysis_run_reconstruction_update_reject;
        alter table analysis_run_lineage_edge
            enable trigger analysis_run_lineage_edge_update_reject;
    end if;
    if to_regclass('public.analysis_run_tepp_result') is not null then
        alter table analysis_run_tepp_result
            enable trigger analysis_run_tepp_result_update_reject;
    end if;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        alter table analysis_source_snapshot_member
            enable trigger analysis_source_snapshot_member_update_reject;
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
    'Empties immutable registry, reconstruction, TEPP result, membership, '
    'and outbox relations after an unrevoked role grant, '
    'analysis_run_retention_admin membership, and the documented approval '
    'token; records one analysis_run_retention_event. Next action: export '
    'that event, delete it, then roll back 0028, 0023, 0022, 0021, 0020, '
    'and 0018.';

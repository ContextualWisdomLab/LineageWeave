-- Durable analysis-run start outbox (ADR 0023).
--
-- Start appends Running and one immutable outbox row in the same
-- transaction. Reconstruct and TEPP then run from that row so a crash
-- no longer rolls the work item back to Pending. Valkey carries the
-- wake-up; PostgreSQL stays the source of truth. No post body or
-- fabricated psychometric score is stored.

insert into common_lookup_value (
    lookup_category, lookup_code, lookup_label, display_order
) values
    ('analysis_outbox_delivery', 'analysis_outbox_claimed', 'Claimed', 0),
    ('analysis_outbox_delivery', 'analysis_outbox_delivered', 'Delivered', 1)
on conflict (lookup_code) do nothing;

create table if not exists analysis_run_outbox (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    work_kind_code text not null,
    request_sha256 text not null,
    enqueued_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    constraint analysis_run_outbox_kind_check
        check (work_kind_code in ('analysis_run_lineage', 'analysis_run_tepp')),
    constraint analysis_run_outbox_digest_check
        check (request_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_outbox_time_check
        check (enqueued_at <= recorded_at)
);

comment on table analysis_run_outbox is
    'One immutable start-work item per analysis run; never a post body '
    'or a fabricated psychometric score.';

create table if not exists analysis_run_outbox_delivery (
    analysis_run_id uuid not null
        references analysis_run_outbox (analysis_run_id),
    delivery_ordinal integer not null,
    delivery_status_code text not null,
    occurred_at timestamptz not null,
    valkey_stream_entry_id text,
    primary key (analysis_run_id, delivery_ordinal),
    constraint analysis_run_outbox_delivery_ordinal_check
        check (delivery_ordinal >= 1),
    constraint analysis_run_outbox_delivery_status_check
        check (
            delivery_status_code in (
                'analysis_outbox_claimed',
                'analysis_outbox_delivered'
            )
        ),
    constraint analysis_run_outbox_delivery_stream_check
        check (
            valkey_stream_entry_id is null
            or char_length(valkey_stream_entry_id) between 1 and 64
        )
);

comment on table analysis_run_outbox_delivery is
    'Append-only claim and delivery events for one start-work item.';

create or replace function reject_analysis_run_outbox_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_outbox_is_immutable';
end
$$;

comment on function reject_analysis_run_outbox_mutation() is
    'Rejects mutation of an enqueued start-work item.';

drop trigger if exists analysis_run_outbox_mutation_reject
    on analysis_run_outbox;
create trigger analysis_run_outbox_mutation_reject
before update or delete on analysis_run_outbox
for each row execute function reject_analysis_run_outbox_mutation();

create or replace function reject_analysis_run_outbox_delivery_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_outbox_delivery_is_append_only';
end
$$;

comment on function reject_analysis_run_outbox_delivery_mutation() is
    'Rejects mutation of a start-work delivery event.';

drop trigger if exists analysis_run_outbox_delivery_mutation_reject
    on analysis_run_outbox_delivery;
create trigger analysis_run_outbox_delivery_mutation_reject
before update or delete on analysis_run_outbox_delivery
for each row execute function reject_analysis_run_outbox_delivery_mutation();

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
            delete from analysis_run_reconstruction;
        end if;
        if to_regclass('public.analysis_source_snapshot_member') is not null then
            delete from analysis_source_snapshot_member;
        end if;
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
    'Empties immutable registry, reconstruction, membership, and outbox '
    'relations after an unrevoked role grant, analysis_run_retention_admin '
    'membership, and the documented approval token; records one '
    'analysis_run_retention_event. Next action: export that event, delete '
    'it, then roll back 0023, 0022, 0021, 0020, and 0018.';

-- Normalized provenance for private, direct-source product analysis.
--
-- The registry intentionally stores no source SQL, DSN, raw post content,
-- source-table name, image bytes, provider credentials, or arbitrary JSON
-- payload. Operator-owned source definitions and acceptance artifacts remain
-- outside this database and are linked only through opaque identifiers and
-- immutable digests.

begin;

insert into common_lookup_value (
    lookup_category,
    lookup_code,
    lookup_label,
    display_order
)
values
    ('analysis_run_kind', 'analysis_run_lineage', 'Lineage reconstruction', 10),
    ('analysis_run_kind', 'analysis_run_report', 'Periodic report generation', 20),
    ('analysis_run_kind', 'analysis_run_tepp', 'TEPP measurement', 30),
    ('analysis_run_status', 'analysis_status_pending', 'Pending', 10),
    ('analysis_run_status', 'analysis_status_running', 'Running', 20),
    ('analysis_run_status', 'analysis_status_succeeded', 'Succeeded', 30),
    ('analysis_run_status', 'analysis_status_failed', 'Failed', 40),
    ('analysis_run_status', 'analysis_status_cancelled', 'Cancelled', 50),
    ('analysis_run_scope', 'analysis_scope_all_visible', 'All visible records', 10),
    ('analysis_run_scope', 'analysis_scope_corporate_entity', 'Corporate entity', 20),
    ('analysis_run_scope', 'analysis_scope_process_unit', 'Process unit', 30),
    ('analysis_run_scope', 'analysis_scope_thread_group', 'Thread group', 40),
    ('analysis_source_count', 'analysis_count_source_row', 'Source rows', 10),
    ('analysis_source_count', 'analysis_count_document', 'Documents', 20),
    ('analysis_source_count', 'analysis_count_thread', 'Threads', 30),
    ('analysis_source_count', 'analysis_count_lineage_node', 'Lineage nodes', 40),
    ('analysis_source_count', 'analysis_count_lineage_edge', 'Lineage edges', 50)
on conflict (lookup_code) do nothing;

do $$
begin
    if exists (
        select 1
        from (
            values
                ('analysis_run_lineage', 'analysis_run_kind'),
                ('analysis_run_report', 'analysis_run_kind'),
                ('analysis_run_tepp', 'analysis_run_kind'),
                ('analysis_status_pending', 'analysis_run_status'),
                ('analysis_status_running', 'analysis_run_status'),
                ('analysis_status_succeeded', 'analysis_run_status'),
                ('analysis_status_failed', 'analysis_run_status'),
                ('analysis_status_cancelled', 'analysis_run_status'),
                ('analysis_scope_all_visible', 'analysis_run_scope'),
                ('analysis_scope_corporate_entity', 'analysis_run_scope'),
                ('analysis_scope_process_unit', 'analysis_run_scope'),
                ('analysis_scope_thread_group', 'analysis_run_scope'),
                ('analysis_count_source_row', 'analysis_source_count'),
                ('analysis_count_document', 'analysis_source_count'),
                ('analysis_count_thread', 'analysis_source_count'),
                ('analysis_count_lineage_node', 'analysis_source_count'),
                ('analysis_count_lineage_edge', 'analysis_source_count')
        ) as expected_lookup(lookup_code, lookup_category)
        join common_lookup_value actual_lookup
          on actual_lookup.lookup_code = expected_lookup.lookup_code
        where actual_lookup.lookup_category <> expected_lookup.lookup_category
    ) then
        raise exception 'analysis_run_registry_lookup_conflict';
    end if;
end
$$;

create table if not exists analysis_source_snapshot (
    analysis_source_snapshot_id uuid primary key default uuid_generate_v4(),
    snapshot_sha256 text not null unique,
    source_contract_version text not null,
    maximum_available_time timestamptz not null,
    captured_at timestamptz not null,
    created_at timestamptz not null default now(),
    constraint analysis_source_snapshot_digest_check
        check (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_source_snapshot_contract_check
        check (length(btrim(source_contract_version)) between 1 and 128),
    constraint analysis_source_snapshot_capture_check
        check (maximum_available_time <= captured_at)
);

comment on table analysis_source_snapshot is
    'Immutable identity and availability boundary for one private source snapshot; no source text or source-table name is stored.';

create table if not exists analysis_source_count (
    analysis_source_count_id uuid primary key default uuid_generate_v4(),
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id)
        on delete cascade,
    count_type_code text not null
        references common_lookup_value (lookup_code),
    count_value bigint not null,
    created_at timestamptz not null default now(),
    constraint analysis_source_count_nonnegative_check
        check (count_value >= 0),
    constraint analysis_source_count_kind_check
        check (
            count_type_code in (
                'analysis_count_source_row',
                'analysis_count_document',
                'analysis_count_thread',
                'analysis_count_lineage_node',
                'analysis_count_lineage_edge'
            )
        ),
    unique (analysis_source_snapshot_id, count_type_code)
);

comment on table analysis_source_count is
    'One normalized aggregate count per immutable source snapshot and count vocabulary; values are evidence, not source records.';

create table if not exists analysis_run (
    analysis_run_id uuid primary key default uuid_generate_v4(),
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id),
    run_kind_code text not null
        references common_lookup_value (lookup_code),
    idempotency_key text not null,
    requested_by_account_id uuid not null
        references user_account (user_account_id),
    knowledge_cutoff timestamptz not null,
    configuration_schema_version text not null,
    configuration_sha256 text not null,
    model_profile_identifier text,
    prompt_digest_sha256 text,
    code_revision_sha text not null,
    requested_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    constraint analysis_run_kind_check
        check (
            run_kind_code in (
                'analysis_run_lineage',
                'analysis_run_report',
                'analysis_run_tepp'
            )
        ),
    constraint analysis_run_idempotency_check
        check (length(btrim(idempotency_key)) between 1 and 255),
    constraint analysis_run_configuration_version_check
        check (
            length(btrim(configuration_schema_version)) between 1 and 128
        ),
    constraint analysis_run_configuration_digest_check
        check (configuration_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_model_profile_check
        check (
            model_profile_identifier is null
            or length(btrim(model_profile_identifier)) between 1 and 255
        ),
    constraint analysis_run_prompt_digest_check
        check (
            prompt_digest_sha256 is null
            or prompt_digest_sha256 ~ '^[0-9a-f]{64}$'
        ),
    constraint analysis_run_revision_check
        check (code_revision_sha ~ '^[0-9a-f]{40}$'),
    unique (requested_by_account_id, idempotency_key)
);

comment on table analysis_run is
    'One immutable, account-scoped analysis request bound to a source snapshot, run-owned knowledge cutoff, and reproducibility digests; current state is derived from status events.';

create table if not exists analysis_run_scope (
    analysis_run_scope_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id) on delete cascade,
    scope_kind_code text not null
        references common_lookup_value (lookup_code),
    scope_key text,
    created_at timestamptz not null default now(),
    constraint analysis_run_scope_kind_check
        check (
            scope_kind_code in (
                'analysis_scope_all_visible',
                'analysis_scope_corporate_entity',
                'analysis_scope_process_unit',
                'analysis_scope_thread_group'
            )
        ),
    constraint analysis_run_scope_shape_check
        check (
            (
                scope_kind_code = 'analysis_scope_all_visible'
                and scope_key is null
            )
            or (
                scope_kind_code <> 'analysis_scope_all_visible'
                and scope_key is not null
                and length(btrim(scope_key)) between 1 and 255
            )
        ),
    unique (analysis_run_id, scope_kind_code, scope_key)
);

comment on table analysis_run_scope is
    'Normalized product scope for one analysis run; visible-record authorization remains authoritative.';

create table if not exists analysis_run_status_event (
    analysis_run_status_event_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id) on delete cascade,
    status_ordinal integer not null,
    status_code text not null
        references common_lookup_value (lookup_code),
    occurred_at timestamptz not null,
    recorded_at timestamptz not null default now(),
    failure_code text,
    retryable boolean not null default false,
    constraint analysis_run_status_ordinal_check
        check (status_ordinal >= 1),
    constraint analysis_run_status_code_check
        check (
            status_code in (
                'analysis_status_pending',
                'analysis_status_running',
                'analysis_status_succeeded',
                'analysis_status_failed',
                'analysis_status_cancelled'
            )
        ),
    constraint analysis_run_status_time_check
        check (occurred_at <= recorded_at),
    constraint analysis_run_status_failure_shape_check
        check (
            (
                status_code = 'analysis_status_failed'
                and failure_code is not null
                and length(btrim(failure_code)) between 1 and 128
            )
            or (
                status_code <> 'analysis_status_failed'
                and failure_code is null
                and retryable = false
            )
        ),
    unique (analysis_run_id, status_ordinal)
);

comment on table analysis_run_status_event is
    'Append-only, contiguous, monotonic lifecycle evidence for one analysis run.';

create index if not exists analysis_run_requested_at_idx
    on analysis_run (requested_at desc, analysis_run_id desc);

create index if not exists analysis_run_snapshot_idx
    on analysis_run (analysis_source_snapshot_id);

create index if not exists analysis_run_status_event_time_idx
    on analysis_run_status_event (
        analysis_run_id,
        occurred_at desc,
        status_ordinal desc
    );

create or replace function reject_analysis_source_snapshot_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_snapshot_is_immutable';
end
$$;

drop trigger if exists analysis_source_snapshot_update_reject
    on analysis_source_snapshot;

create trigger analysis_source_snapshot_update_reject
before update on analysis_source_snapshot
for each row execute function reject_analysis_source_snapshot_update();

create or replace function reject_analysis_source_count_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_count_is_immutable';
end
$$;

drop trigger if exists analysis_source_count_update_reject
    on analysis_source_count;

create trigger analysis_source_count_update_reject
before update on analysis_source_count
for each row execute function reject_analysis_source_count_update();

create or replace function enforce_analysis_run_knowledge_cutoff()
returns trigger
language plpgsql
as $$
declare
    source_maximum_available_time timestamptz;
begin
    select maximum_available_time
      into source_maximum_available_time
      from analysis_source_snapshot
     where analysis_source_snapshot_id = new.analysis_source_snapshot_id
     for update;

    if not found then
        raise exception 'analysis_source_snapshot_missing';
    end if;

    if source_maximum_available_time > new.knowledge_cutoff then
        raise exception 'analysis_run_future_information_leakage';
    end if;

    return new;
end
$$;

drop trigger if exists analysis_run_knowledge_cutoff_guard
    on analysis_run;

create trigger analysis_run_knowledge_cutoff_guard
before insert on analysis_run
for each row execute function enforce_analysis_run_knowledge_cutoff();

create or replace function reject_analysis_run_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_request_is_immutable';
end
$$;

drop trigger if exists analysis_run_mutation_reject
    on analysis_run;

create trigger analysis_run_mutation_reject
before update or delete on analysis_run
for each row execute function reject_analysis_run_mutation();

create or replace function enforce_analysis_source_count_freeze()
returns trigger
language plpgsql
as $$
declare
    affected_snapshot_id uuid;
begin
    if tg_op = 'DELETE' then
        affected_snapshot_id := old.analysis_source_snapshot_id;
    else
        affected_snapshot_id := new.analysis_source_snapshot_id;
    end if;

    perform 1
      from analysis_source_snapshot
     where analysis_source_snapshot_id = affected_snapshot_id
     for update;

    if exists (
        select 1
          from analysis_run
         where analysis_source_snapshot_id = affected_snapshot_id
    ) then
        raise exception 'analysis_source_count_frozen_after_run';
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end
$$;

drop trigger if exists analysis_source_count_freeze_guard
    on analysis_source_count;

create trigger analysis_source_count_freeze_guard
before insert or delete on analysis_source_count
for each row execute function enforce_analysis_source_count_freeze();

create or replace function enforce_analysis_run_status_transition()
returns trigger
language plpgsql
as $$
declare
    previous_status analysis_run_status_event%rowtype;
begin
    perform 1
      from analysis_run
     where analysis_run_id = new.analysis_run_id
     for update;

    if not found then
        raise exception 'analysis_run_missing';
    end if;

    select *
      into previous_status
      from analysis_run_status_event
     where analysis_run_id = new.analysis_run_id
     order by status_ordinal desc
     limit 1;

    if not found then
        if new.status_ordinal <> 1
           or new.status_code <> 'analysis_status_pending' then
            raise exception 'analysis_run_first_status_must_be_pending';
        end if;
        return new;
    end if;

    if previous_status.status_code in (
        'analysis_status_succeeded',
        'analysis_status_failed',
        'analysis_status_cancelled'
    ) then
        raise exception 'analysis_run_terminal_status_is_final';
    end if;

    if new.status_ordinal <> previous_status.status_ordinal + 1 then
        raise exception 'analysis_run_status_ordinal_must_be_contiguous';
    end if;

    if new.occurred_at < previous_status.occurred_at then
        raise exception 'analysis_run_status_time_must_be_monotonic';
    end if;

    if not (
        (
            previous_status.status_code = 'analysis_status_pending'
            and new.status_code in (
                'analysis_status_running',
                'analysis_status_failed',
                'analysis_status_cancelled'
            )
        )
        or (
            previous_status.status_code = 'analysis_status_running'
            and new.status_code in (
                'analysis_status_succeeded',
                'analysis_status_failed',
                'analysis_status_cancelled'
            )
        )
    ) then
        raise exception 'analysis_run_status_transition_is_invalid';
    end if;

    return new;
end
$$;

drop trigger if exists analysis_run_status_transition_guard
    on analysis_run_status_event;

create trigger analysis_run_status_transition_guard
before insert on analysis_run_status_event
for each row execute function enforce_analysis_run_status_transition();

create or replace function reject_analysis_run_status_event_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_status_event_is_append_only';
end
$$;

drop trigger if exists analysis_run_status_event_update_reject
    on analysis_run_status_event;

create trigger analysis_run_status_event_update_reject
before update on analysis_run_status_event
for each row execute function reject_analysis_run_status_event_mutation();

drop trigger if exists analysis_run_status_event_delete_reject
    on analysis_run_status_event;

create trigger analysis_run_status_event_delete_reject
before delete on analysis_run_status_event
for each row execute function reject_analysis_run_status_event_mutation();

create or replace view analysis_run_current_status as
select
    analysis_run_id,
    analysis_run_status_event_id,
    status_ordinal,
    status_code,
    occurred_at,
    recorded_at,
    failure_code,
    retryable
from (
    select
        status_event.*,
        row_number() over (
            partition by status_event.analysis_run_id
            order by status_event.status_ordinal desc
        ) as status_rank
    from analysis_run_status_event status_event
) ranked_status
where status_rank = 1;

commit;

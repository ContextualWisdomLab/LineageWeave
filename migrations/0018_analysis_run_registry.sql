-- Milestone 2 additive runtime bridge: normalized analysis-run registry.
--
-- This migration records reproducibility, authorization scope, aggregate
-- reconciliation, and lifecycle evidence without storing source SQL, DSNs,
-- raw records, image bytes, provider payloads, credentials, or free-form JSON.
-- Snapshot availability is evidence-owned; the knowledge cutoff is run-owned,
-- so one immutable capture can support multiple historically valid analyses.

begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('analysis_run_kind', 'analysis_run_lineage', 'Lineage reconstruction', 0),
    ('analysis_run_kind', 'analysis_run_report', 'Period report', 1),
    ('analysis_run_kind', 'analysis_run_tepp', 'TEPP measurement', 2),
    ('analysis_run_status', 'analysis_status_pending', 'Pending', 0),
    ('analysis_run_status', 'analysis_status_running', 'Running', 1),
    ('analysis_run_status', 'analysis_status_succeeded', 'Succeeded', 2),
    ('analysis_run_status', 'analysis_status_failed', 'Failed', 3),
    ('analysis_run_status', 'analysis_status_cancelled', 'Cancelled', 4),
    ('analysis_run_scope', 'analysis_scope_all_visible', 'All authorized records', 0),
    ('analysis_run_scope', 'analysis_scope_corporate_entity', 'Corporate entity', 1),
    ('analysis_run_scope', 'analysis_scope_process_unit', 'Process unit', 2),
    ('analysis_run_scope', 'analysis_scope_thread_group', 'Thread group', 3),
    ('analysis_source_count', 'analysis_count_source_row', 'Source rows', 0),
    ('analysis_source_count', 'analysis_count_document', 'Documents', 1),
    ('analysis_source_count', 'analysis_count_thread', 'Threads', 2),
    ('analysis_source_count', 'analysis_count_lineage_node', 'Lineage nodes', 3),
    ('analysis_source_count', 'analysis_count_lineage_edge', 'Lineage edges', 4)
on conflict (lookup_code) do nothing;

-- common_lookup_value deliberately makes lookup_code globally unique. A code
-- that already exists under another category is a migration conflict rather
-- than permission to attach the wrong vocabulary to an analysis column.
do $$
declare
    lookup_mismatch_count integer;
begin
    select count(*)
      into lookup_mismatch_count
      from common_lookup_value as actual
      join (values
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
      ) as expected(lookup_code, lookup_category)
        on expected.lookup_code = actual.lookup_code
     where actual.lookup_category <> expected.lookup_category;

    if lookup_mismatch_count <> 0 then
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
        check (maximum_available_time <= captured_at),
    constraint analysis_source_snapshot_created_check
        check (captured_at <= created_at)
);

comment on table analysis_source_snapshot is
    'Immutable captured-source identity and latest evidence-availability time; '
    'knowledge cutoffs belong to analysis_run, not the reusable snapshot.';

create table if not exists analysis_source_count (
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id)
        on delete cascade,
    count_type_code text not null
        references common_lookup_value (lookup_code),
    count_value bigint not null,
    primary key (analysis_source_snapshot_id, count_type_code),
    constraint analysis_source_count_type_check
        check (count_type_code in (
            'analysis_count_source_row',
            'analysis_count_document',
            'analysis_count_thread',
            'analysis_count_lineage_node',
            'analysis_count_lineage_edge'
        )),
    constraint analysis_source_count_nonnegative_check
        check (count_value >= 0)
);

comment on table analysis_source_count is
    'One normalized aggregate reconciliation count per immutable snapshot and '
    'count vocabulary; no source record is stored.';

create table if not exists analysis_run (
    analysis_run_id uuid primary key default uuid_generate_v4(),
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id),
    run_kind_code text not null
        references common_lookup_value (lookup_code),
    requested_by_account_id uuid not null
        references user_account (user_account_id),
    idempotency_key text not null,
    knowledge_cutoff timestamptz not null,
    configuration_schema_version text not null,
    configuration_sha256 text not null,
    model_contract_sha256 text,
    prompt_bundle_sha256 text,
    code_revision_sha text not null,
    requested_at timestamptz not null default now(),
    constraint analysis_run_kind_check
        check (run_kind_code in (
            'analysis_run_lineage',
            'analysis_run_report',
            'analysis_run_tepp'
        )),
    constraint analysis_run_idempotency_key_check
        check (
            idempotency_key = btrim(idempotency_key)
            and length(idempotency_key) between 1 and 256
            and idempotency_key !~ '[[:cntrl:]]'
        ),
    constraint analysis_run_configuration_version_check
        check (
            configuration_schema_version = btrim(configuration_schema_version)
            and length(configuration_schema_version) between 1 and 128
        ),
    constraint analysis_run_configuration_digest_check
        check (configuration_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_model_digest_check
        check (
            model_contract_sha256 is null
            or model_contract_sha256 ~ '^[0-9a-f]{64}$'
        ),
    constraint analysis_run_prompt_digest_check
        check (
            prompt_bundle_sha256 is null
            or prompt_bundle_sha256 ~ '^[0-9a-f]{64}$'
        ),
    constraint analysis_run_code_revision_check
        check (code_revision_sha ~ '^(?:[0-9a-f]{40}|[0-9a-f]{64})$'),
    constraint analysis_run_request_time_check
        check (knowledge_cutoff <= requested_at),
    unique (requested_by_account_id, idempotency_key)
);

create index if not exists analysis_run_snapshot_idx
    on analysis_run (analysis_source_snapshot_id);
create index if not exists analysis_run_kind_requested_idx
    on analysis_run (run_kind_code, requested_at desc);
create index if not exists analysis_run_requester_idx
    on analysis_run (requested_by_account_id, requested_at desc);

comment on table analysis_run is
    'Immutable account-scoped analysis request bound to one snapshot, one '
    'knowledge cutoff, and reproducibility digests; lifecycle is event-derived.';

create table if not exists analysis_run_scope (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    scope_kind_code text not null
        references common_lookup_value (lookup_code),
    corporate_entity_id uuid
        references corporate_entity (corporate_entity_id),
    process_unit_id uuid
        references process_unit (process_unit_id),
    scope_key text,
    constraint analysis_run_scope_kind_check
        check (scope_kind_code in (
            'analysis_scope_all_visible',
            'analysis_scope_corporate_entity',
            'analysis_scope_process_unit',
            'analysis_scope_thread_group'
        )),
    constraint analysis_run_scope_shape_check
        check (
            (scope_kind_code = 'analysis_scope_all_visible'
                and corporate_entity_id is null
                and process_unit_id is null
                and scope_key is null)
            or
            (scope_kind_code = 'analysis_scope_corporate_entity'
                and corporate_entity_id is not null
                and process_unit_id is null
                and scope_key is null)
            or
            (scope_kind_code = 'analysis_scope_process_unit'
                and corporate_entity_id is null
                and process_unit_id is not null
                and scope_key is null)
            or
            (scope_kind_code = 'analysis_scope_thread_group'
                and corporate_entity_id is null
                and process_unit_id is null
                and scope_key is not null
                and scope_key = btrim(scope_key)
                and length(scope_key) between 1 and 256
                and scope_key !~ '[[:cntrl:]]')
        )
);

create index if not exists analysis_run_scope_entity_idx
    on analysis_run_scope (corporate_entity_id)
    where corporate_entity_id is not null;
create index if not exists analysis_run_scope_unit_idx
    on analysis_run_scope (process_unit_id)
    where process_unit_id is not null;

comment on table analysis_run_scope is
    'One immutable authorization-relevant scope is required before lifecycle '
    'evidence; process-unit ownership remains derivable from process_unit.';

create table if not exists analysis_run_status_event (
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id),
    status_ordinal integer not null,
    status_code text not null
        references common_lookup_value (lookup_code),
    occurred_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    failure_code text,
    retryable boolean not null default false,
    primary key (analysis_run_id, status_ordinal),
    constraint analysis_run_status_code_check
        check (status_code in (
            'analysis_status_pending',
            'analysis_status_running',
            'analysis_status_succeeded',
            'analysis_status_failed',
            'analysis_status_cancelled'
        )),
    constraint analysis_run_status_ordinal_check
        check (status_ordinal >= 1),
    constraint analysis_run_status_time_check
        check (occurred_at <= recorded_at),
    constraint analysis_run_status_failure_shape_check
        check (
            (status_code = 'analysis_status_failed'
                and failure_code is not null
                and failure_code ~ '^[a-z][a-z0-9_]{0,127}$')
            or
            (status_code <> 'analysis_status_failed'
                and failure_code is null
                and retryable = false)
        )
);

create index if not exists analysis_run_status_current_idx
    on analysis_run_status_event (analysis_run_id, status_ordinal desc);

comment on table analysis_run_status_event is
    'Append-only, contiguous, monotonic state-machine evidence; failure_code is '
    'a bounded machine code and never contains raw provider or source payloads.';

create or replace function reject_analysis_source_snapshot_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_snapshot_is_immutable';
end
$$;

comment on function reject_analysis_source_snapshot_update() is
    'Rejects mutation of captured source identity and availability evidence.';

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

comment on function reject_analysis_source_count_update() is
    'Rejects replacement of a snapshot aggregate; delete and reinsert is only '
    'permitted before the snapshot is attached to a run.';

drop trigger if exists analysis_source_count_update_reject
    on analysis_source_count;
create trigger analysis_source_count_update_reject
before update on analysis_source_count
for each row execute function reject_analysis_source_count_update();

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

    -- Both count mutation and run creation lock this row first. That common
    -- lock order closes the race between the final count write and first run.
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

comment on function enforce_analysis_source_count_freeze() is
    'Serializes count insert/delete against first run creation and rejects '
    'changes after any run references the snapshot.';

drop trigger if exists analysis_source_count_freeze_guard
    on analysis_source_count;
create trigger analysis_source_count_freeze_guard
before insert or delete on analysis_source_count
for each row execute function enforce_analysis_source_count_freeze();

create or replace function enforce_analysis_run_knowledge_cutoff()
returns trigger
language plpgsql
as $$
declare
    snapshot_available_time timestamptz;
    snapshot_capture_time timestamptz;
begin
    if new.requested_at > clock_timestamp() then
        raise exception 'analysis_run_request_time_in_future';
    end if;

    select maximum_available_time, captured_at
      into snapshot_available_time, snapshot_capture_time
      from analysis_source_snapshot
     where analysis_source_snapshot_id = new.analysis_source_snapshot_id
     for update;

    if not found then
        raise exception 'analysis_source_snapshot_not_found';
    end if;
    if snapshot_available_time > new.knowledge_cutoff then
        raise exception 'analysis_run_future_information_leakage';
    end if;
    if snapshot_capture_time > new.requested_at then
        raise exception 'analysis_run_snapshot_captured_after_request';
    end if;
    return new;
end
$$;

comment on function enforce_analysis_run_knowledge_cutoff() is
    'Locks the immutable snapshot and rejects run cutoffs earlier than the '
    'latest admitted evidence or requests earlier than snapshot capture.';

drop trigger if exists analysis_run_knowledge_cutoff_guard
    on analysis_run;
create trigger analysis_run_knowledge_cutoff_guard
before insert on analysis_run
for each row execute function enforce_analysis_run_knowledge_cutoff();

drop trigger if exists analysis_run_update_reject
    on analysis_run;
drop trigger if exists analysis_run_mutation_reject
    on analysis_run;
drop function if exists reject_analysis_run_update();

create or replace function reject_analysis_run_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_request_is_immutable';
end
$$;

comment on function reject_analysis_run_mutation() is
    'Rejects update or delete of actor, cutoff, idempotency, and reproducibility '
    'evidence; run progress belongs to append-only status events.';

create trigger analysis_run_mutation_reject
before update or delete on analysis_run
for each row execute function reject_analysis_run_mutation();

create or replace function reject_analysis_run_scope_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_scope_is_immutable';
end
$$;

comment on function reject_analysis_run_scope_mutation() is
    'Rejects update or delete of the authorization-relevant scope attached to '
    'an immutable analysis request.';

drop trigger if exists analysis_run_scope_mutation_reject
    on analysis_run_scope;
create trigger analysis_run_scope_mutation_reject
before update or delete on analysis_run_scope
for each row execute function reject_analysis_run_scope_mutation();

create or replace function reject_analysis_run_status_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_status_event_is_append_only';
end
$$;

comment on function reject_analysis_run_status_mutation() is
    'Rejects update or delete of state-machine evidence.';

drop trigger if exists analysis_run_status_event_update_reject
    on analysis_run_status_event;
create trigger analysis_run_status_event_update_reject
before update on analysis_run_status_event
for each row execute function reject_analysis_run_status_mutation();

drop trigger if exists analysis_run_status_event_delete_reject
    on analysis_run_status_event;
create trigger analysis_run_status_event_delete_reject
before delete on analysis_run_status_event
for each row execute function reject_analysis_run_status_mutation();

create or replace function enforce_analysis_run_status_transition()
returns trigger
language plpgsql
as $$
declare
    previous_ordinal integer;
    previous_status_code text;
    previous_occurred_at timestamptz;
    run_requested_at timestamptz;
    database_now timestamptz;
begin
    -- The immutable parent row is a per-run serialization lock. It prevents
    -- concurrent writers from both accepting the same next ordinal.
    select requested_at
      into run_requested_at
      from analysis_run
     where analysis_run_id = new.analysis_run_id
     for update;

    if not found then
        raise exception 'analysis_run_not_found';
    end if;
    if not exists (
        select 1 from analysis_run_scope
         where analysis_run_id = new.analysis_run_id
    ) then
        raise exception 'analysis_run_scope_required';
    end if;
    if new.occurred_at < run_requested_at then
        raise exception 'analysis_run_status_before_request';
    end if;
    -- Permit bounded client clock skew, but do not accept arbitrary future
    -- events that would manufacture audit time. Do not clamp occurred_at
    -- down: that would break monotonicity against Python-ahead events.
    database_now := clock_timestamp();
    if new.occurred_at > database_now + interval '1 minute' then
        raise exception 'analysis_run_status_time_too_far_in_future';
    end if;
    new.recorded_at := greatest(database_now, new.occurred_at);

    select status_ordinal, status_code, occurred_at
      into previous_ordinal, previous_status_code, previous_occurred_at
      from analysis_run_status_event
     where analysis_run_id = new.analysis_run_id
     order by status_ordinal desc
     limit 1;

    if previous_ordinal is null then
        if new.status_ordinal <> 1
           or new.status_code <> 'analysis_status_pending' then
            raise exception 'analysis_run_first_status_must_be_pending';
        end if;
        return new;
    end if;

    if new.status_ordinal <> previous_ordinal + 1 then
        raise exception 'analysis_run_status_ordinal_not_contiguous';
    end if;
    if new.occurred_at < previous_occurred_at then
        raise exception 'analysis_run_status_time_not_monotonic';
    end if;

    if previous_status_code = 'analysis_status_pending' then
        if new.status_code not in (
            'analysis_status_running',
            'analysis_status_cancelled'
        ) then
            raise exception 'analysis_run_status_transition_invalid';
        end if;
    elsif previous_status_code = 'analysis_status_running' then
        if new.status_code not in (
            'analysis_status_succeeded',
            'analysis_status_failed',
            'analysis_status_cancelled'
        ) then
            raise exception 'analysis_run_status_transition_invalid';
        end if;
    else
        raise exception 'analysis_run_terminal_status_has_no_successor';
    end if;

    return new;
end
$$;

comment on function enforce_analysis_run_status_transition() is
    'Serializes status appends and requires immutable scope, request-time '
    'ordering, recorded time at least as late as occurrence, legal transitions, '
    'and terminal finality.';

drop trigger if exists analysis_run_status_transition_guard
    on analysis_run_status_event;
create trigger analysis_run_status_transition_guard
before insert on analysis_run_status_event
for each row execute function enforce_analysis_run_status_transition();

create or replace view analysis_run_current_status as
select distinct on (status_event.analysis_run_id)
       status_event.analysis_run_id,
       status_event.status_code,
       status_event.status_ordinal,
       status_event.occurred_at,
       status_event.recorded_at,
       status_event.failure_code,
       status_event.retryable
  from analysis_run_status_event as status_event
 order by status_event.analysis_run_id,
          status_event.status_ordinal desc;

comment on view analysis_run_current_status is
    'Latest append-only status projection for each run; never a second mutable '
    'lifecycle authority.';

commit;

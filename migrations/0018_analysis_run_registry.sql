-- Milestone 2 additive runtime bridge: normalized analysis-run registry.
--
-- The retained direct-PostgreSQL experiment stored repeated counts and an
-- unconstrained metadata JSON object in one run row. This migration preserves
-- the useful run/snapshot evidence without copying that parallel product
-- schema. Source content, source-table names, credentials, provider payloads,
-- raw exceptions, and organization-specific identifiers are not stored here.
--
-- Database objects remain descriptive two-or-more-word snake_case and every
-- multi-valued fact is represented by a separate relation.

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

-- A globally unique lookup_code is already the repository-wide contract. A
-- pre-existing code under another category is a schema conflict, not a reason
-- to silently accept the wrong vocabulary.
do $$
declare
    mismatch_count integer;
begin
    select count(*)
      into mismatch_count
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

    if mismatch_count <> 0 then
        raise exception 'analysis_run_registry_lookup_conflict';
    end if;
end
$$;

create table if not exists analysis_source_snapshot (
    analysis_source_snapshot_id uuid primary key default uuid_generate_v4(),
    snapshot_sha256 text not null,
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
    constraint analysis_source_snapshot_identity_unique
        unique (snapshot_sha256, source_contract_version)
);

comment on table analysis_source_snapshot is
    'Immutable source-capture identity and latest evidence-availability time. '
    'Analysis-specific knowledge cutoffs belong to analysis_run.';

create or replace function reject_analysis_source_snapshot_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_snapshot_is_immutable';
end
$$;

comment on function reject_analysis_source_snapshot_update() is
    'Rejects mutation of immutable source-capture identity and clocks.';

drop trigger if exists analysis_source_snapshot_update_reject
    on analysis_source_snapshot;
create trigger analysis_source_snapshot_update_reject
before update on analysis_source_snapshot
for each row execute function reject_analysis_source_snapshot_update();

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
    'One immutable aggregate count per source snapshot and count vocabulary.';

create or replace function reject_analysis_source_count_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_count_is_immutable';
end
$$;

comment on function reject_analysis_source_count_update() is
    'Rejects rewriting a persisted source-snapshot count.';

drop trigger if exists analysis_source_count_update_reject
    on analysis_source_count;
create trigger analysis_source_count_update_reject
before update on analysis_source_count
for each row execute function reject_analysis_source_count_update();

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
        check (length(btrim(idempotency_key)) between 1 and 256),
    constraint analysis_run_configuration_version_check
        check (length(btrim(configuration_schema_version)) between 1 and 128),
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
    constraint analysis_run_requester_idempotency_unique
        unique (requested_by_account_id, idempotency_key)
);

create index if not exists analysis_run_snapshot_idx
    on analysis_run (analysis_source_snapshot_id);
create index if not exists analysis_run_kind_requested_idx
    on analysis_run (run_kind_code, requested_at desc);
create index if not exists analysis_run_requester_idx
    on analysis_run (requested_by_account_id, requested_at desc);

comment on table analysis_run is
    'Immutable, account-scoped analysis request bound to one source snapshot, '
    'one knowledge cutoff, and reproducibility digests.';

create or replace function enforce_analysis_run_knowledge_cutoff()
returns trigger
language plpgsql
as $$
declare
    snapshot_available_time timestamptz;
begin
    select maximum_available_time
      into snapshot_available_time
      from analysis_source_snapshot
     where analysis_source_snapshot_id = new.analysis_source_snapshot_id
     for update;

    if not found then
        raise exception 'analysis_source_snapshot_not_found';
    end if;

    if snapshot_available_time > new.knowledge_cutoff then
        raise exception 'analysis_run_future_information_leakage';
    end if;

    return new;
end
$$;

comment on function enforce_analysis_run_knowledge_cutoff() is
    'Serializes run creation with count-set changes and rejects source evidence '
    'that was unavailable at the run knowledge cutoff.';

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

comment on function reject_analysis_run_mutation() is
    'Rejects update/delete of a registered analysis request and its digests.';

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

    -- Both count-set changes and run creation lock the same parent row. This
    -- closes the race in which a run could start while another transaction was
    -- still extending or deleting the aggregate evidence set.
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
    'Allows count insert/delete only before the first run references a snapshot.';

drop trigger if exists analysis_source_count_freeze_guard
    on analysis_source_count;
create trigger analysis_source_count_freeze_guard
before insert or delete on analysis_source_count
for each row execute function enforce_analysis_source_count_freeze();

create table if not exists analysis_run_scope (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id)
        on delete cascade,
    scope_kind_code text not null
        references common_lookup_value (lookup_code),
    corporate_entity_id uuid
        references corporate_entity (corporate_entity_id),
    process_unit_id uuid
        references process_unit (process_unit_id),
    scope_key text,
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
                and length(btrim(scope_key)) between 1 and 256)
        )
);

create index if not exists analysis_run_scope_entity_idx
    on analysis_run_scope (corporate_entity_id)
    where corporate_entity_id is not null;
create index if not exists analysis_run_scope_unit_idx
    on analysis_run_scope (process_unit_id)
    where process_unit_id is not null;

comment on table analysis_run_scope is
    'At most one authorization-relevant product scope for a run; process-unit '
    'ownership remains derivable from process_unit.';

create or replace function reject_analysis_run_scope_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_scope_is_immutable';
end
$$;

comment on function reject_analysis_run_scope_update() is
    'Rejects mutation of the authorization scope attached to a run.';

drop trigger if exists analysis_run_scope_update_reject
    on analysis_run_scope;
create trigger analysis_run_scope_update_reject
before update on analysis_run_scope
for each row execute function reject_analysis_run_scope_update();

create table if not exists analysis_run_status_event (
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id)
        on delete cascade,
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
    constraint analysis_run_status_recorded_check
        check (occurred_at <= recorded_at),
    constraint analysis_run_status_failure_shape_check
        check (
            (status_code = 'analysis_status_failed'
                and failure_code is not null
                and length(btrim(failure_code)) between 1 and 128)
            or
            (status_code <> 'analysis_status_failed'
                and failure_code is null
                and retryable = false)
        )
);

create index if not exists analysis_run_status_current_idx
    on analysis_run_status_event (analysis_run_id, status_ordinal desc);

comment on table analysis_run_status_event is
    'Append-only, contiguous state-machine evidence with separate occurrence '
    'and database record clocks.';

create or replace function lock_analysis_run_status_append()
returns trigger
language plpgsql
as $$
begin
    -- Serialize all status appends for one run across concurrent transactions.
    perform 1
      from analysis_run
     where analysis_run_id = new.analysis_run_id
     for update;

    if not found then
        raise exception 'analysis_run_not_found';
    end if;

    return new;
end
$$;

comment on function lock_analysis_run_status_append() is
    'Locks one analysis run before status rows are appended.';

drop trigger if exists analysis_run_status_append_lock
    on analysis_run_status_event;
create trigger analysis_run_status_append_lock
before insert on analysis_run_status_event
for each row execute function lock_analysis_run_status_append();

create or replace function enforce_analysis_run_status_transition()
returns trigger
language plpgsql
as $$
declare
    invalid_history_exists boolean;
begin
    -- AFTER-row triggers execute after the statement, so a multi-row INSERT is
    -- validated as one complete history rather than depending on VALUES order.
    select exists (
        select 1
          from (
              select status_ordinal,
                     status_code,
                     occurred_at,
                     lag(status_ordinal) over (
                         order by status_ordinal
                     ) as previous_status_ordinal,
                     lag(status_code) over (
                         order by status_ordinal
                     ) as previous_status_code,
                     lag(occurred_at) over (
                         order by status_ordinal
                     ) as previous_occurred_at
                from analysis_run_status_event
               where analysis_run_id = new.analysis_run_id
          ) as history
         where (
                  previous_status_ordinal is null
                  and (
                      status_ordinal <> 1
                      or status_code <> 'analysis_status_pending'
                  )
               )
            or (
                  previous_status_ordinal is not null
                  and status_ordinal <> previous_status_ordinal + 1
               )
            or (
                  previous_occurred_at is not null
                  and occurred_at < previous_occurred_at
               )
            or (
                  previous_status_code is not null
                  and not (
                      (
                          previous_status_code = 'analysis_status_pending'
                          and status_code in (
                              'analysis_status_running',
                              'analysis_status_failed',
                              'analysis_status_cancelled'
                          )
                      )
                      or (
                          previous_status_code = 'analysis_status_running'
                          and status_code in (
                              'analysis_status_succeeded',
                              'analysis_status_failed',
                              'analysis_status_cancelled'
                          )
                      )
                  )
               )
    ) into invalid_history_exists;

    if invalid_history_exists then
        raise exception 'analysis_run_status_history_invalid';
    end if;

    return new;
end
$$;

comment on function enforce_analysis_run_status_transition() is
    'Enforces initial pending state, contiguous ordinals, monotonic occurrence '
    'time, legal transitions, and terminal-state finality.';

drop trigger if exists analysis_run_status_transition_guard
    on analysis_run_status_event;
create trigger analysis_run_status_transition_guard
after insert on analysis_run_status_event
for each row execute function enforce_analysis_run_status_transition();

create or replace function reject_analysis_run_status_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_status_event_is_append_only';
end
$$;

comment on function reject_analysis_run_status_mutation() is
    'Rejects update/delete of analysis_run_status_event so history stays append-only.';

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
    'Latest append-only status event for each run; not a second state authority.';

commit;

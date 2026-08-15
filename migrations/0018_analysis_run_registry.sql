-- Milestone 2 additive runtime bridge: normalized analysis-run registry.
--
-- The closed direct-PostgreSQL prototype stored repeated counts and an
-- unconstrained metadata JSON object in one analysis_run_records row.  This
-- migration preserves the useful run/snapshot evidence without copying the
-- prototype table or its parallel product schema.  Source content, credentials,
-- provider payloads, and cross-service application rows are not stored here.
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

-- A globally unique lookup_code is already the repository-wide contract.  A
-- pre-existing code under another category is therefore a schema conflict, not
-- a reason to silently accept the wrong vocabulary.
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
    snapshot_sha256 text not null unique,
    source_contract_version text not null,
    knowledge_cutoff timestamptz not null,
    captured_at timestamptz not null,
    created_at timestamptz not null default now(),
    constraint analysis_source_snapshot_digest_check
        check (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_source_snapshot_contract_check
        check (length(btrim(source_contract_version)) between 1 and 128),
    constraint analysis_source_snapshot_cutoff_check
        check (knowledge_cutoff <= captured_at)
);

comment on table analysis_source_snapshot is
    'Immutable identity and temporal eligibility boundary for one source snapshot; no source text or source-table name is stored.';

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
    'One normalized aggregate count per snapshot and count vocabulary; values are aggregate acceptance evidence, not source records.';

create table if not exists analysis_run (
    analysis_run_id uuid primary key default uuid_generate_v4(),
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id),
    run_kind_code text not null
        references common_lookup_value (lookup_code),
    idempotency_key text not null unique,
    requested_by_account_id uuid
        references user_account (user_account_id),
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
        check (model_contract_sha256 is null or model_contract_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_prompt_digest_check
        check (prompt_bundle_sha256 is null or prompt_bundle_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_code_revision_check
        check (code_revision_sha ~ '^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
);

create index if not exists analysis_run_snapshot_idx
    on analysis_run (analysis_source_snapshot_id);
create index if not exists analysis_run_kind_requested_idx
    on analysis_run (run_kind_code, requested_at desc);
create index if not exists analysis_run_requester_idx
    on analysis_run (requested_by_account_id)
    where requested_by_account_id is not null;

comment on table analysis_run is
    'One idempotent analysis request bound to a source snapshot and reproducibility digests; current state is derived from status events.';

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
    'At most one authorization-relevant product scope for a run; process-unit ownership is derived from process_unit instead of duplicated.';

create table if not exists analysis_run_status_event (
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id)
        on delete cascade,
    status_ordinal integer not null,
    status_code text not null
        references common_lookup_value (lookup_code),
    occurred_at timestamptz not null,
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
    'Append-only run-state evidence. Failure codes are bounded machine codes; raw provider exceptions and source content are excluded.';

create or replace function reject_analysis_run_status_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_status_event_is_append_only';
end
$$;

comment on function reject_analysis_run_status_mutation() is
    'Rejects update/delete of analysis_run_status_event so run history remains append-only.';

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
       status_event.failure_code,
       status_event.retryable
  from analysis_run_status_event as status_event
 order by status_event.analysis_run_id,
          status_event.status_ordinal desc;

comment on view analysis_run_current_status is
    'Read projection of the latest append-only status event for each run; it is not a second state authority.';

commit;

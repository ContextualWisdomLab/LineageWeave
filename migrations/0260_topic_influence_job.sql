-- ADR 0210: durable producer lease for the external fast-mlsirm result.
-- The job carries no scores and never substitutes for a producer artifact.

create table if not exists topic_influence_job (
    topic_model_run_id uuid primary key
        references topic_model_run (topic_model_run_id) on delete cascade,
    status_code text not null
        check (status_code in ('queued', 'awaiting_evidence', 'running', 'succeeded', 'failed')),
    request_sha256 text check (request_sha256 ~ '^[0-9a-f]{64}$'),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    failure_code text check (
        failure_code is null or failure_code in (
            'input_evidence_incomplete',
            'producer_unavailable',
            'producer_result_invalid',
            'persistence_failed'
        )
    ),
    queued_at timestamptz not null default clock_timestamp(),
    not_before timestamptz not null default clock_timestamp(),
    started_at timestamptz,
    lease_expires_at timestamptz,
    lease_token uuid,
    completed_at timestamptz,
    check (
        (status_code = 'queued' and started_at is null and lease_expires_at is null and lease_token is null and completed_at is null)
        or (status_code = 'awaiting_evidence' and started_at is null and lease_expires_at is null and lease_token is null and completed_at is not null)
        or (status_code = 'running' and started_at is not null and lease_expires_at is not null and lease_token is not null and completed_at is null)
        or (status_code in ('succeeded', 'failed') and started_at is not null and lease_expires_at is null and lease_token is null and completed_at is not null)
    )
);

alter table topic_influence_job
    add column if not exists lease_expires_at timestamptz,
    add column if not exists lease_token uuid;

alter table topic_influence_job
    drop constraint if exists topic_influence_job_status_code_check,
    drop constraint if exists topic_influence_job_check;

-- A pre-lease branch deployment cannot supply a declared expiry after the
-- fact. Release that interrupted claim; the next worker claim records the
-- configured lease contract before invoking the producer.
update topic_influence_job
   set status_code = 'queued', request_sha256 = null, started_at = null,
       completed_at = null, failure_code = null,
       not_before = clock_timestamp(),
       lease_expires_at = null, lease_token = null
 where status_code = 'running'
   and (lease_expires_at is null or lease_token is null);

alter table topic_influence_job
    add constraint topic_influence_job_status_code_check
        check (status_code in (
            'queued', 'awaiting_evidence', 'running', 'succeeded', 'failed'
        )),
    add constraint topic_influence_job_check check (
        (status_code = 'queued'
            and started_at is null
            and lease_expires_at is null
            and lease_token is null
            and completed_at is null)
        or (status_code = 'awaiting_evidence'
            and started_at is null
            and lease_expires_at is null
            and lease_token is null
            and completed_at is not null)
        or (status_code = 'running'
            and started_at is not null
            and lease_expires_at is not null
            and lease_token is not null
            and completed_at is null)
        or (status_code in ('succeeded', 'failed')
            and started_at is not null
            and lease_expires_at is null
            and lease_token is null
            and completed_at is not null)
    );

create index if not exists topic_influence_job_queue_idx
    on topic_influence_job (status_code, not_before, queued_at, topic_model_run_id)
    where status_code = 'queued';

create or replace function queue_topic_influence_job()
returns trigger
language plpgsql
as $$
begin
    insert into topic_influence_job (topic_model_run_id, status_code)
    values (new.topic_model_run_id, 'queued')
    on conflict (topic_model_run_id) do nothing;
    return new;
end
$$;

create or replace function wake_topic_influence_job_for_model()
returns trigger
language plpgsql
as $$
begin
    update topic_influence_job
       set status_code = 'queued', failure_code = null, completed_at = null,
           not_before = clock_timestamp()
     where topic_model_run_id = new.topic_model_run_id
       and status_code = 'awaiting_evidence';
    return new;
end
$$;

create or replace function wake_topic_influence_job_for_analysis()
returns trigger
language plpgsql
as $$
begin
    update topic_influence_job job
       set status_code = 'queued', failure_code = null, completed_at = null,
           not_before = clock_timestamp()
      from topic_model_run model
     where model.analysis_run_id = new.analysis_run_id
       and job.topic_model_run_id = model.topic_model_run_id
       and job.status_code = 'awaiting_evidence';
    return new;
end
$$;

drop trigger if exists topic_model_run_influence_queue on topic_model_run;
create trigger topic_model_run_influence_queue
after insert on topic_model_run
for each row execute function queue_topic_influence_job();

drop trigger if exists topic_model_run_influence_wake on topic_model_run;
create trigger topic_model_run_influence_wake after update on topic_model_run
for each row execute function wake_topic_influence_job_for_model();

drop trigger if exists analysis_run_influence_wake on analysis_run;
create trigger analysis_run_influence_wake
after update of knowledge_cutoff, analysis_source_snapshot_id on analysis_run
for each row execute function wake_topic_influence_job_for_analysis();

drop trigger if exists topic_coordinate_influence_wake on topic_post_coordinate;
create trigger topic_coordinate_influence_wake
after insert or update on topic_post_coordinate
for each row execute function wake_topic_influence_job_for_model();

drop trigger if exists topic_membership_influence_wake on topic_context_membership;
create trigger topic_membership_influence_wake
after insert or update on topic_context_membership
for each row execute function wake_topic_influence_job_for_model();

drop trigger if exists topic_definition_influence_wake on topic_definition;
create trigger topic_definition_influence_wake
after insert or update on topic_definition
for each row execute function wake_topic_influence_job_for_model();

create or replace function wake_topic_influence_job_for_provenance_binding()
returns trigger
language plpgsql
as $$
begin
    update topic_influence_job job
       set status_code = 'queued', failure_code = null, completed_at = null,
           not_before = clock_timestamp()
      from topic_context_membership membership
      join provenance_assertion assertion
        on assertion.assertion_id = membership.provenance_assertion_id
       and assertion.relation_code = 'prov_was_derived_from'
     where assertion.object_resource_id = new.resource_id
       and new.node_type_code = 'node_post'
       and membership.source_post_id = new.node_id
       and job.topic_model_run_id = membership.topic_model_run_id
       and job.status_code = 'awaiting_evidence';
    if tg_op = 'UPDATE' then
        update topic_influence_job job
           set status_code = 'queued', failure_code = null, completed_at = null,
               not_before = clock_timestamp()
          from topic_context_membership membership
          join provenance_assertion assertion
            on assertion.assertion_id = membership.provenance_assertion_id
           and assertion.relation_code = 'prov_was_derived_from'
         where assertion.object_resource_id = old.resource_id
           and old.node_type_code = 'node_post'
           and membership.source_post_id = old.node_id
           and job.topic_model_run_id = membership.topic_model_run_id
           and job.status_code = 'awaiting_evidence';
    end if;
    return new;
end
$$;

drop trigger if exists topic_provenance_binding_influence_wake
    on provenance_resource_binding;
create trigger topic_provenance_binding_influence_wake
after insert or update on provenance_resource_binding
for each row execute function wake_topic_influence_job_for_provenance_binding();

create or replace function wake_topic_influence_job_for_provenance_assertion()
returns trigger
language plpgsql
as $$
begin
    update topic_influence_job job
       set status_code = 'queued', failure_code = null, completed_at = null,
           not_before = clock_timestamp()
      from topic_context_membership membership
     where membership.provenance_assertion_id = new.assertion_id
       and job.topic_model_run_id = membership.topic_model_run_id
       and job.status_code = 'awaiting_evidence';
    return new;
end
$$;

drop trigger if exists topic_provenance_assertion_influence_wake
    on provenance_assertion;
create trigger topic_provenance_assertion_influence_wake
after update of object_resource_id, relation_code on provenance_assertion
for each row execute function wake_topic_influence_job_for_provenance_assertion();

-- Older topic-lineage envelopes and calibrated-measurement receipts are not
-- the accepted posterior projection. Remove candidate triggers that could
-- wake this queue from those scientifically distinct records.
drop trigger if exists topic_tepp_receipt_influence_wake on analysis_run_tepp_receipt;
drop trigger if exists topic_terminal_influence_wake on analysis_run_topic_lineage_result;

insert into topic_influence_job (topic_model_run_id, status_code)
select model.topic_model_run_id, 'queued'
  from topic_model_run model
 where not exists (
           select 1
             from topic_influence_run influence
            where influence.topic_model_run_id = model.topic_model_run_id
       )
on conflict (topic_model_run_id) do nothing;

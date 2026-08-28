-- ADR 0210: durable producer lease for the external fast-mlsirm result.
-- The job carries no scores and never substitutes for a producer artifact.

create table if not exists topic_influence_job (
    topic_model_run_id uuid primary key
        references topic_model_run (topic_model_run_id) on delete cascade,
    status_code text not null
        check (status_code in ('queued', 'running', 'succeeded', 'failed')),
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
    started_at timestamptz,
    completed_at timestamptz,
    check (
        (status_code = 'queued' and started_at is null and completed_at is null)
        or (status_code = 'running' and started_at is not null and completed_at is null)
        or (status_code in ('succeeded', 'failed') and started_at is not null and completed_at is not null)
    )
);

create index if not exists topic_influence_job_queue_idx
    on topic_influence_job (status_code, queued_at, topic_model_run_id)
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

drop trigger if exists topic_model_run_influence_queue on topic_model_run;
create trigger topic_model_run_influence_queue
after insert on topic_model_run
for each row execute function queue_topic_influence_job();

insert into topic_influence_job (topic_model_run_id, status_code)
select model.topic_model_run_id, 'queued'
  from topic_model_run model
 where not exists (
           select 1
             from topic_influence_run influence
            where influence.topic_model_run_id = model.topic_model_run_id
       )
on conflict (topic_model_run_id) do nothing;


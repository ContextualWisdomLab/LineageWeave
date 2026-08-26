-- ADR 0253: distinguish successful empty extraction from unavailable evidence.

create table if not exists post_occupational_construct_extraction (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    orchestrator_session_id text not null check (btrim(orchestrator_session_id) <> ''),
    generated_at timestamptz not null default now()
);

create index if not exists post_occupational_construct_extraction_digest_idx
    on post_occupational_construct_extraction (source_body_sha256, post_id);

-- A prior successful content run predates this required evidence channel. Requeue
-- it once; replay is a no-op after a matching extraction-run row exists.
with requeue_candidate as materialized (
    select job.post_id,
           coalesce(max(event.status_ordinal), -1) + 1 as status_ordinal
      from post_content_ingestion_job job
      left join post_content_ingestion_job_status_event event
        on event.post_id = job.post_id
      left join post_occupational_construct_extraction extraction
        on extraction.post_id = job.post_id
       and extraction.source_body_sha256 = job.source_body_sha256
     where job.status_code = 'post_content_ingestion_succeeded'
       and extraction.post_id is null
     group by job.post_id
), requeued as (
    update post_content_ingestion_job job
       set status_code = 'post_content_ingestion_queued',
           attempt_count = 0,
           queued_at = now(),
           started_at = null,
           completed_at = null,
           updated_at = now(),
           last_error_code = null,
           last_error_detail = null
      from requeue_candidate candidate
     where job.post_id = candidate.post_id
    returning job.post_id
)
insert into post_content_ingestion_job_status_event
    (post_id, status_ordinal, status_code, detail_text)
select requeued.post_id, candidate.status_ordinal,
       'post_content_ingestion_queued',
       'required occupational construct evidence channel added'
  from requeued
  join requeue_candidate candidate on candidate.post_id = requeued.post_id;

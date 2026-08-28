-- ADR 0098 amendment: provider admission deferral is durable queue timing,
-- not a consumed provider attempt.
alter table post_content_ingestion_job
    add column if not exists next_attempt_at timestamptz;

create index if not exists post_content_ingestion_next_attempt_idx
    on post_content_ingestion_job (status_code, next_attempt_at, queued_at);

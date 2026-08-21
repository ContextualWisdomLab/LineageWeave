-- ADR 0098: PostgreSQL is the durable post-content job ledger; Valkey is only
-- the wake-up transport. The body never enters the queue payload.
create table if not exists post_content_ingestion_job (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    status_code text not null check (
        status_code in (
            'post_content_ingestion_queued',
            'post_content_ingestion_running',
            'post_content_ingestion_succeeded',
            'post_content_ingestion_failed'
        )
    ),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    queued_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now(),
    last_error_code text,
    last_error_detail text
);

create table if not exists post_content_ingestion_job_status_event (
    post_id uuid not null references post_content_ingestion_job(post_id) on delete cascade,
    status_ordinal integer not null check (status_ordinal >= 0),
    status_code text not null check (
        status_code in (
            'post_content_ingestion_queued',
            'post_content_ingestion_running',
            'post_content_ingestion_succeeded',
            'post_content_ingestion_failed'
        )
    ),
    occurred_at timestamptz not null default now(),
    failure_code text,
    detail_text text,
    primary key (post_id, status_ordinal)
);

create index if not exists post_content_ingestion_job_status_idx
    on post_content_ingestion_job (status_code, queued_at);

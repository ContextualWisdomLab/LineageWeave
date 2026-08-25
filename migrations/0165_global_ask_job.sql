-- Global Ask asynchronous job queue.
--
-- A reader's Ask no longer blocks one HTTP request on a multi-minute LLM
-- round-trip through the shared orchestrator: POST /api/ask persists a
-- job row, wakes the in-process worker through the Valkey stream, and
-- the frontend polls GET /api/ask/jobs/{id} until the job settles.
-- Mirrors the durable-row-plus-stream design post_content_job already
-- uses, so a lost stream entry is recovered from the queued rows.

create table if not exists global_ask_job (
    global_ask_job_id uuid primary key default uuid_generate_v4(),
    requesting_account_id uuid not null references user_account (user_account_id),
    question_text text not null,
    job_status_code text not null default 'queued'
        check (job_status_code in ('queued', 'running', 'succeeded', 'failed')),
    answer_payload jsonb,
    failure_detail text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table global_ask_job is
    'One asynchronous Global Ask request: queued by POST /api/ask, '
    'processed by the Valkey-stream worker, polled by the reader.';

create index if not exists global_ask_job_account_idx
    on global_ask_job (requesting_account_id, created_at desc);

create index if not exists global_ask_job_queued_idx
    on global_ask_job (created_at)
    where job_status_code = 'queued';

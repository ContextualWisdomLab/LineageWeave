-- ADR 0098 amendment: bounded failure provenance identifies the failed channel
-- without storing source content, prompts, provider responses, or credentials.
alter table post_content_ingestion_job
    add column if not exists failure_channel_stage_code text,
    add column if not exists failure_http_status integer,
    add column if not exists failure_orchestrator_error_code text,
    add column if not exists failure_retryable boolean,
    add column if not exists failure_session_correlation_id text;

alter table post_content_ingestion_job
    drop constraint if exists post_content_failure_http_status_check;
alter table post_content_ingestion_job
    add constraint post_content_failure_http_status_check
    check (failure_http_status is null or failure_http_status between 100 and 599);

alter table post_content_ingestion_job
    drop constraint if exists post_content_failure_session_length_check;
alter table post_content_ingestion_job
    add constraint post_content_failure_session_length_check
    check (
        failure_session_correlation_id is null
        or length(failure_session_correlation_id) between 1 and 128
    );

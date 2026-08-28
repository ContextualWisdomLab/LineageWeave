-- ADR 0098 amendment: closed error classes identify the local failure boundary.
alter table post_content_ingestion_job
    add column if not exists failure_error_type text;

alter table post_content_ingestion_job
    drop constraint if exists post_content_failure_error_type_check;
alter table post_content_ingestion_job
    add constraint post_content_failure_error_type_check
    check (
        failure_error_type is null
        or failure_error_type in (
            'http_client_error',
            'timeout_error',
            'key_error',
            'os_error',
            'value_error',
            'runtime_error',
            'internal_error'
        )
    );

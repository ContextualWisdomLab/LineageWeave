-- Migration 0234 / ADR 0098 amendment: validation failures retain only a closed code and JSON path.
alter table post_content_ingestion_job
    add column if not exists failure_validation_code text,
    add column if not exists failure_validation_path text;

alter table post_content_ingestion_job
    drop constraint if exists post_content_failure_validation_check;
alter table post_content_ingestion_job
    add constraint post_content_failure_validation_check
    check (
        (failure_validation_code is null and failure_validation_path is null)
        or (
            failure_validation_code = 'operations_case_evidence_contract'
            and failure_validation_path = '$.cases'
        )
    );

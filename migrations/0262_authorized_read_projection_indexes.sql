-- Migration 0262 / ADR 0271: keep authorization reads off the wide source heap.
create index concurrently if not exists source_post_active_context_access_idx
    on source_post (
        visibility_code,
        corporate_entity_id,
        process_unit_id,
        coalesce(event_occurred_at, created_at),
        post_id
    )
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
      and (
          nullif(btrim(source_author_code), '') is not null
          or nullif(btrim(source_author_name), '') is not null
          or nullif(btrim(source_company_code), '') is not null
          or nullif(btrim(source_company_name), '') is not null
          or nullif(btrim(source_process_unit_code), '') is not null
          or nullif(btrim(source_process_unit_name), '') is not null
          or nullif(btrim(source_sales_pool_code), '') is not null
          or nullif(btrim(source_sales_pool_name), '') is not null
          or nullif(btrim(source_customer_code), '') is not null
          or nullif(btrim(source_customer_name), '') is not null
          or nullif(btrim(source_project_code), '') is not null
          or nullif(btrim(source_project_name), '') is not null
      );

create index concurrently if not exists source_post_active_access_idx
    on source_post (
        visibility_code,
        corporate_entity_id,
        process_unit_id,
        coalesce(event_occurred_at, created_at),
        post_id
    )
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '');

create index concurrently if not exists post_content_ingestion_failed_post_idx
    on post_content_ingestion_job (post_id)
    where status_code = 'post_content_ingestion_failed';

create index concurrently if not exists post_content_ingestion_status_read_idx
    on post_content_ingestion_job (post_id, status_code);

create index concurrently if not exists post_voice_assertion_open_read_idx
    on post_voice_classification_assertion (
        post_id,
        voice_concept_code,
        assertion_status_code,
        valid_from
    )
    where valid_to is null;

create index concurrently if not exists post_voice_assertion_bounded_read_idx
    on post_voice_classification_assertion (
        valid_to,
        valid_from,
        post_id,
        voice_concept_code,
        assertion_status_code
    )
    where valid_to is not null;

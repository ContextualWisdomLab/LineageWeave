-- Reverse 0168. created_at stays the record ingestion clock.

alter table source_post
    drop column if exists event_occurred_at;

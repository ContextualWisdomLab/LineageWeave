-- Rollback for 0183_global_ask_job_conversation_context.sql.
alter table global_ask_job
    drop column if exists anchor_post_id,
    drop column if exists conversation_id;

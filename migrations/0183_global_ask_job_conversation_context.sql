-- Carry the reader's conversation and anchor-post context from submission
-- (POST /api/ask) through to the worker that actually answers the
-- question, so the settled job can persist its turn into the same
-- global_ask_conversation the reader is continuing (ADR 0105) instead of
-- always starting a fresh one. Both are nullable: a first turn has no
-- conversation_id yet, and a question is not always anchored to a post.

alter table global_ask_job
    add column if not exists conversation_id uuid,
    add column if not exists anchor_post_id uuid references source_post (post_id);

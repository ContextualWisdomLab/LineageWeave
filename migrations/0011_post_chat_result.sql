-- Persisted in-popup Q&A for a source_post.
-- GET /api/posts/{id}/chat and POST /api/posts/{id}/chat read this first
-- so a seeded demo stack can answer Ask without a live LLM. Live
-- answers still write through the same tables. CREATE IF NOT EXISTS so
-- a volume that already ran 0001 still upgrades.

create table if not exists post_chat_result (
    post_id uuid not null references source_post (post_id) on delete cascade,
    question_norm text not null,
    question_text text not null,
    answer_text text not null,
    computed_at timestamptz not null default now(),
    primary key (post_id, question_norm)
);

create table if not exists post_chat_citation (
    post_id uuid not null,
    question_norm text not null,
    citation_ordinal integer not null,
    cited_post_id uuid not null references source_post (post_id) on delete cascade,
    primary key (post_id, question_norm, citation_ordinal),
    foreign key (post_id, question_norm)
        references post_chat_result (post_id, question_norm) on delete cascade
);

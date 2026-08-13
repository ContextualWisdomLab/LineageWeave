-- Persisted Korean summary / key events / R&R for a source_post.
-- GET /api/posts/{id}/summary reads this first so a seeded demo stack
-- is not empty when the LLM orchestrator is off. Live derivation still
-- writes through the same tables.

create table if not exists post_summary_result (
    post_id uuid primary key references source_post (post_id) on delete cascade,
    korean_summary text not null,
    computed_at timestamptz not null default now()
);

create table if not exists post_summary_event (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    event_ordinal integer not null,
    event_text text not null,
    primary key (post_id, event_ordinal)
);

create table if not exists post_summary_role (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    person_name text not null,
    responsibility text not null,
    primary key (post_id, person_name)
);

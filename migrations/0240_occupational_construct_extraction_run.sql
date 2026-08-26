-- ADR 0251: distinguish successful empty extraction from unavailable evidence.

create table if not exists post_occupational_construct_extraction (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    orchestrator_session_id text not null check (btrim(orchestrator_session_id) <> ''),
    generated_at timestamptz not null default now()
);

create index if not exists post_occupational_construct_extraction_digest_idx
    on post_occupational_construct_extraction (source_body_sha256, post_id);

-- Persist semantic project candidates separately from imported field hints.
-- Reports may use only candidates above the application threshold while the
-- evidence and confidence remain available for review.
create table if not exists post_project_mention (
    post_id uuid not null references source_post (post_id) on delete cascade,
    project_key text not null,
    project_name text not null,
    evidence_text text not null,
    confidence numeric(4,3) not null check (confidence >= 0 and confidence <= 1),
    ontology_iri text not null,
    extraction_method text not null,
    created_at timestamptz not null default now(),
    primary key (post_id, project_key)
);

create index if not exists post_project_mention_key_idx
    on post_project_mention (project_key, confidence desc);

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

do $$
declare
    confidence_column text;
begin
    if exists (
        select 1
          from information_schema.columns
         where table_schema = 'public'
           and table_name = 'post_project_mention'
           and column_name = 'mention_confidence'
    ) then
        confidence_column := 'mention_confidence';
    else
        confidence_column := 'confidence';
    end if;
    execute format(
        'create index if not exists post_project_mention_key_idx '
        'on post_project_mention (project_key, %s desc)',
        confidence_column
    );
end
$$;

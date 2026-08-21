-- Search support for misspelled identifiers and semantic evidence.
-- The query still applies RBAC/ABAC before these fuzzy predicates.
begin;

create extension if not exists pg_trgm;

create index if not exists source_post_id_trgm_idx
    on source_post using gin ((replace(post_id::text, '-', '')) gin_trgm_ops);
create index if not exists source_post_title_trgm_idx
    on source_post using gin (post_title gin_trgm_ops);
create index if not exists source_post_secondary_grouping_trgm_idx
    on source_post using gin (secondary_grouping_key gin_trgm_ops);
create index if not exists post_project_mention_name_trgm_idx
    on post_project_mention using gin (project_name gin_trgm_ops);
create index if not exists post_summary_role_actor_trgm_idx
    on post_summary_role using gin (actor_name gin_trgm_ops);
create index if not exists cataloged_person_name_trgm_idx
    on cataloged_person using gin (person_name gin_trgm_ops);

commit;

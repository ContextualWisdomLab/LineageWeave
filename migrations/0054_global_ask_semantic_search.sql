begin;

-- Global Ask performs multilingual contains-search on persisted semantic fields.
-- One trigram index per searched column keeps the predicate indexable; do not
-- replace these predicates with concat_ws(...) because expression scans cannot
-- use the column indexes below.
create extension if not exists pg_trgm;

create index if not exists post_project_mention_name_search_idx
    on post_project_mention using gin (project_name gin_trgm_ops);
create index if not exists post_project_mention_evidence_search_idx
    on post_project_mention using gin (evidence_text gin_trgm_ops);
create index if not exists post_project_mention_ontology_search_idx
    on post_project_mention using gin (ontology_iri gin_trgm_ops);

create index if not exists post_summary_role_actor_search_idx
    on post_summary_role using gin (actor_name gin_trgm_ops);
create index if not exists post_summary_role_responsibility_search_idx
    on post_summary_role using gin (responsibility gin_trgm_ops);
create index if not exists post_summary_role_affiliation_search_idx
    on post_summary_role using gin (affiliated_organization_name gin_trgm_ops);

create index if not exists post_person_mention_context_search_idx
    on post_person_mention using gin (mention_context gin_trgm_ops);
create index if not exists cataloged_person_name_search_idx
    on cataloged_person using gin (person_name gin_trgm_ops);
create index if not exists cataloged_person_title_search_idx
    on cataloged_person using gin (last_known_job_title gin_trgm_ops);

create index if not exists corporate_entity_name_search_idx
    on corporate_entity using gin (entity_name gin_trgm_ops);
create index if not exists cataloged_team_name_search_idx
    on cataloged_team using gin (team_name gin_trgm_ops);
create index if not exists cataloged_team_affiliation_search_idx
    on cataloged_team using gin (affiliated_organization_name gin_trgm_ops);

commit;

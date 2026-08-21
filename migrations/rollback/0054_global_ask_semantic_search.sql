begin;

drop index if exists cataloged_team_affiliation_search_idx;
drop index if exists cataloged_team_name_search_idx;
drop index if exists corporate_entity_name_search_idx;
drop index if exists cataloged_person_title_search_idx;
drop index if exists cataloged_person_name_search_idx;
drop index if exists post_person_mention_context_search_idx;
drop index if exists post_summary_role_affiliation_search_idx;
drop index if exists post_summary_role_responsibility_search_idx;
drop index if exists post_summary_role_actor_search_idx;
drop index if exists post_project_mention_ontology_search_idx;
drop index if exists post_project_mention_evidence_search_idx;
drop index if exists post_project_mention_name_search_idx;

-- pg_trgm may be shared by other product slices; rollback owns only its indexes.
commit;

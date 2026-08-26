-- Native PostgreSQL full-text indexes for Global Ask semantic nomination.
-- The expressions match backend/app/global_ask_semantic_candidates.py.
create index concurrently if not exists post_project_mention_search_fts_idx
    on post_project_mention using gin (
        to_tsvector(
            'simple',
            coalesce(project_key, '') || ' ' || coalesce(project_name, '') || ' ' ||
            coalesce(evidence_text, '') || ' ' || coalesce(ontology_iri, '')
        )
    );

create index concurrently if not exists post_summary_role_search_fts_idx
    on post_summary_role using gin (
        to_tsvector(
            'simple',
            coalesce(actor_name, '') || ' ' || coalesce(responsibility, '') || ' ' ||
            coalesce(affiliated_organization_name, '')
        )
    );

create index concurrently if not exists cataloged_person_search_fts_idx
    on cataloged_person using gin (
        to_tsvector(
            'simple', coalesce(person_name, '') || ' ' ||
                      coalesce(last_known_job_title, '')
        )
    );

create index concurrently if not exists post_person_mention_context_fts_idx
    on post_person_mention using gin (
        to_tsvector('simple', coalesce(mention_context, ''))
    );

create index concurrently if not exists corporate_entity_name_fts_idx
    on corporate_entity using gin (to_tsvector('simple', entity_name));

create index concurrently if not exists cataloged_team_search_fts_idx
    on cataloged_team using gin (
        to_tsvector(
            'simple', coalesce(team_name, '') || ' ' ||
                      coalesce(affiliated_organization_name, '')
        )
    );

create index concurrently if not exists knowledge_graph_edge_code_fts_idx
    on knowledge_graph_edge using gin (
        to_tsvector(
            'simple',
            replace(
                coalesce(edge_type_code, '') || ' ' ||
                coalesce(source_node_type_code, '') || ' ' ||
                coalesce(target_node_type_code, ''),
                '_',
                ' '
            )
        )
    );

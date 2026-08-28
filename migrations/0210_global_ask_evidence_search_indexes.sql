-- Index the normalized evidence fields used to nominate Global Ask sources.
-- Rows remain in their owning 3NF tables, and these are expression indexes only.

create index concurrently if not exists post_project_mention_evidence_search_idx
    on post_project_mention using gin (
        to_tsvector(
            'simple',
            coalesce(project_name, '') || ' ' ||
            coalesce(evidence_text, '') || ' ' ||
            coalesce(ontology_iri, '')
        )
    );

create index concurrently if not exists post_summary_role_evidence_search_idx
    on post_summary_role using gin (
        to_tsvector(
            'simple',
            coalesce(actor_name, '') || ' ' ||
            coalesce(responsibility, '') || ' ' ||
            coalesce(affiliated_organization_name, '')
        )
    );

create index concurrently if not exists cataloged_person_evidence_search_idx
    on cataloged_person using gin (
        to_tsvector(
            'simple',
            coalesce(person_name, '') || ' ' ||
            coalesce(last_known_job_title, '')
        )
    );

create index concurrently if not exists person_affiliation_evidence_search_idx
    on person_affiliation using gin (
        to_tsvector(
            'simple',
            coalesce(affiliated_organization_name, '') || ' ' ||
            coalesce(role_title, '')
        )
    );

create index concurrently if not exists corporate_entity_evidence_search_idx
    on corporate_entity using gin (
        to_tsvector(
            'simple',
            coalesce(corporate_entity_code, '') || ' ' ||
            coalesce(entity_name, '')
        )
    );

create index concurrently if not exists cataloged_team_evidence_search_idx
    on cataloged_team using gin (
        to_tsvector(
            'simple',
            coalesce(team_name, '') || ' ' ||
            coalesce(affiliated_organization_name, '')
        )
    );

create index concurrently if not exists source_post_title_evidence_search_idx
    on source_post using gin (
        to_tsvector('simple', coalesce(post_title, ''))
    );

create index concurrently if not exists common_lookup_value_evidence_search_idx
    on common_lookup_value using gin (
        to_tsvector(
            'simple',
            coalesce(lookup_code, '') || ' ' || coalesce(lookup_label, '')
        )
    );

create index concurrently if not exists knowledge_graph_edge_type_search_idx
    on knowledge_graph_edge (edge_type_code, knowledge_graph_edge_id);

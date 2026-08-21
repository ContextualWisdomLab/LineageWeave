-- Explicit source-grounded relations extracted by contextual-orchestrator.
-- Names remain evidence text; this table does not create catalog identity.
create table if not exists post_summary_semantic_relationship (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    relation_ordinal integer not null check (relation_ordinal >= 0),
    subject_name text not null,
    subject_type text not null check (subject_type in (
        'person', 'organization', 'team', 'software_agent',
        'project', 'corporate_entity', 'post'
    )),
    predicate_code text not null check (predicate_code in (
        'org_member_of', 'org_unit_of', 'org_reports_to',
        'skos_broader', 'skos_related', 'prov_was_derived_from',
        'lw_responsible_for', 'lw_supports'
    )),
    object_name text not null,
    object_type text not null check (object_type in (
        'person', 'organization', 'team', 'software_agent',
        'project', 'corporate_entity', 'post'
    )),
    evidence_text text not null,
    relation_confidence numeric(4,3) not null check (relation_confidence >= 0 and relation_confidence <= 1),
    extraction_method text not null default 'contextual_orchestrator_semantic',
    primary key (post_id, relation_ordinal)
);

create index if not exists post_summary_semantic_relationship_post_idx
    on post_summary_semantic_relationship (post_id, relation_ordinal);

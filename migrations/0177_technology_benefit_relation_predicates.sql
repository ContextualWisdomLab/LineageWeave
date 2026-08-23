-- ADR 0146: name which technology a partner provided, who adopted it, and
-- where the adopter intends to apply it.
--
-- Source research could already resolve a partner organization mentioned by
-- a post (e.g. an address match), but the generic semantic relation
-- vocabulary had no predicate for the specific technology/capability that
-- partner provided, which organization received it, or the project/facility
-- the receiving organization intends to apply it to. A buyer asking "which
-- technology, from which partner, applied where" got no structured answer,
-- only free-text evidence buried in an unrelated relation row.
--
-- This migration admits a new `technology` semantic-relation node type and
-- three predicates so a technology-transfer fact decomposes into up to
-- three source-grounded rows sharing the same technology subject:
-- lw_technology_provided_by (technology -> providing organization),
-- lw_technology_adopted_by (technology -> adopting organization), and
-- lw_technology_applied_to (technology -> intended project/facility/place).
-- It deliberately does not write a Voice-of-Partner classification -- "this
-- technology came from this partner" and "this organization is our
-- partner" remain separate judgments, same discipline as ADR 0145.

alter table post_summary_semantic_relationship
    drop constraint if exists post_summary_semantic_relationship_subject_type_check,
    drop constraint if exists post_summary_semantic_relationship_predicate_code_check,
    drop constraint if exists post_summary_semantic_relationship_object_type_check;

alter table post_summary_semantic_relationship
    add constraint post_summary_semantic_relationship_subject_type_check check
        (subject_type in (
            'person', 'organization', 'team', 'software_agent', 'project',
            'corporate_entity', 'post', 'event', 'event_observation',
            'evidence_clue', 'place', 'industrial_asset',
            'industrial_process', 'technology', 'document', 'observation',
            'activity', 'temporal_entity', 'normative_statement',
            'quality_assessment', 'risk_statement', 'organization_context'
        )),
    add constraint post_summary_semantic_relationship_predicate_code_check check
        (predicate_code in (
            'org_member_of', 'org_unit_of', 'org_reports_to',
            'org_has_membership', 'org_role', 'org_organization',
            'org_member_during', 'org_head_of', 'org_suborganization_of',
            'skos_broader', 'skos_related', 'prov_was_derived_from',
            'prov_used', 'prov_was_generated_by', 'prov_was_attributed_to',
            'prov_was_associated_with', 'prov_acted_on_behalf_of',
            'prov_had_primary_source', 'prov_was_influenced_by',
            'prov_specialization_of', 'prov_alternate_of', 'prov_had_member',
            'time_has_time', 'time_before', 'time_after',
            'time_interval_during', 'sosa_has_result',
            'sosa_observed_property', 'sosa_phenomenon_time',
            'sosa_has_feature_of_interest', 'odrl_target', 'odrl_action',
            'odrl_constraint', 'odrl_duty', 'odrl_permission',
            'odrl_prohibition', 'dct_references', 'dct_provenance',
            'dct_conforms_to', 'lw_observes_event', 'lw_clue_for',
            'lw_clue_supports', 'lw_has_cause', 'lw_has_goal',
            'lw_has_consequence', 'lw_has_next_step', 'lw_has_time',
            'lw_at_place', 'lw_has_actor', 'lw_has_result',
            'lw_has_condition', 'lw_inferred_from', 'lw_responsible_for',
            'lw_supports', 'lw_plans_to_operate',
            'lw_technology_provided_by', 'lw_technology_adopted_by',
            'lw_technology_applied_to'
        )),
    add constraint post_summary_semantic_relationship_object_type_check check
        (object_type in (
            'person', 'organization', 'team', 'software_agent', 'project',
            'corporate_entity', 'post', 'event', 'event_observation',
            'evidence_clue', 'place', 'industrial_asset',
            'industrial_process', 'technology', 'document', 'observation',
            'activity', 'temporal_entity', 'normative_statement',
            'quality_assessment', 'risk_statement', 'organization_context'
        ));

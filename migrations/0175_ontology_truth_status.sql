-- Migration 0175: ontology neighborhood truth-status vocabulary (ADR 0168 / issue #341).
-- Instance graph edges stay on knowledge_graph_edge; SKOS broader stays
-- on corporate_entity.parent_entity_id. These lookup rows name the
-- buyer-visible truth status without promoting inference.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('ontology_truth_status', 'truth_authoritative', 'Authoritative', 0),
    ('ontology_truth_status', 'truth_observed', 'Observed', 1),
    ('ontology_truth_status', 'truth_inferred', 'Inferred', 2),
    ('ontology_truth_status', 'truth_proposed', 'Proposed', 3),
    ('ontology_truth_status', 'truth_superseded', 'Superseded', 4),
    ('ontology_truth_status', 'truth_rejected', 'Rejected', 5)
on conflict (lookup_code) do nothing;

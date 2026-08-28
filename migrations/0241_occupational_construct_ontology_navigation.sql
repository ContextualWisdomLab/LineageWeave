-- ADR 0255: expose normalized occupational assertions through the governed
-- ontology neighborhood without duplicating them into knowledge_graph_edge.
insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('node_type', 'node_occupational_construct', 'Occupational construct', 5),
    ('edge_type', 'edge_supports_occupational_construct', 'Supports occupational construct', 7)
on conflict (lookup_code) do nothing;

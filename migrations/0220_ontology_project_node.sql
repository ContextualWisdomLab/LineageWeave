-- Project mentions already persist canonical keys and evidence (ADR 0036).
-- Register their typed ontology projection without duplicating source data.
insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('node_type', 'node_project', 'Project', 4),
    ('edge_type', 'edge_mention_project', 'Project mentioned in', 6)
on conflict (lookup_code) do nothing;

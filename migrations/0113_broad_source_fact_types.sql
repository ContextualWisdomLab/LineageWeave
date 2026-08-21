-- ADR 0129: fact types for observation, organization, industrial, normative,
-- quality, risk, and question-answering dimensions.

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('fact_type', 'fact_observation', 'Observation fact', 2),
    ('fact_type', 'fact_organization', 'Organization fact', 3),
    ('fact_type', 'fact_industrial_asset', 'Industrial asset fact', 4),
    ('fact_type', 'fact_industrial_process', 'Industrial process fact', 5),
    ('fact_type', 'fact_normative', 'Normative fact', 6),
    ('fact_type', 'fact_quality', 'Quality fact', 7),
    ('fact_type', 'fact_risk', 'Risk fact', 8),
    ('fact_type', 'fact_place', 'Place fact', 9),
    ('fact_type', 'fact_actor', 'Actor fact', 10),
    ('fact_type', 'fact_cause', 'Cause fact', 11),
    ('fact_type', 'fact_goal', 'Goal fact', 12),
    ('fact_type', 'fact_result', 'Result fact', 13),
    ('fact_type', 'fact_next_step', 'Next-step fact', 14)
on conflict (lookup_code) do nothing;

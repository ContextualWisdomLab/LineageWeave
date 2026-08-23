begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('measurement_type', 'measurement_budget_amount', 'Budget amount', 0),
    ('measurement_type', 'measurement_capacity', 'Capacity', 1),
    ('measurement_type', 'measurement_daily_capacity', 'Daily capacity', 2),
    ('measurement_unit', 'unit_krw', 'Korean won', 0),
    ('measurement_unit', 'unit_kg', 'Kilogram', 1),
    ('measurement_unit', 'unit_tractor', 'Tractor', 2)
on conflict (lookup_code) do nothing;

create table if not exists post_summary_quantitative_observation (
    post_summary_quantitative_observation_id uuid primary key default uuid_generate_v4(),
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    observation_ordinal integer not null check (observation_ordinal >= 0),
    measurement_type_code text not null references common_lookup_value (lookup_code),
    label_text text not null,
    value_numeric numeric not null check (value_numeric >= 0),
    unit_code text not null references common_lookup_value (lookup_code),
    quantity_numeric numeric check (quantity_numeric is null or quantity_numeric >= 0),
    quantity_unit_code text references common_lookup_value (lookup_code),
    qualifier_text text,
    raw_value_text text not null,
    evidence_text text not null,
    ontology_iri text not null,
    extraction_method text not null,
    unique (post_id, observation_ordinal),
    check ((quantity_numeric is null) = (quantity_unit_code is null))
);

create index if not exists post_summary_quantitative_observation_post_idx
    on post_summary_quantitative_observation (post_id, observation_ordinal);

create index if not exists post_summary_quantitative_observation_type_idx
    on post_summary_quantitative_observation (measurement_type_code, unit_code);

commit;

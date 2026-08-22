begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('fact_type', 'fact_condition', 'Source condition', 0),
    ('fact_type', 'fact_date', 'Source date', 1),
    ('fact_assertion', 'assertion_affirmed', 'Affirmed', 0),
    ('fact_assertion', 'assertion_negated', 'Negated', 1),
    ('fact_assertion', 'assertion_unknown', 'Unknown', 2)
on conflict (lookup_code) do nothing;

create table if not exists post_summary_source_fact (
    post_summary_source_fact_id uuid primary key default uuid_generate_v4(),
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    fact_ordinal integer not null check (fact_ordinal >= 0),
    fact_type_code text not null references common_lookup_value (lookup_code),
    label_text text not null,
    value_text text not null,
    normalized_value_text text,
    assertion_code text references common_lookup_value (lookup_code),
    normalized_date date,
    date_precision_code text check (date_precision_code in ('day', 'month', 'year')),
    normalization_evidence_text text,
    qualifier_text text,
    evidence_text text not null,
    ontology_iri text not null,
    extraction_method text not null,
    unique (post_id, fact_ordinal),
    check (
        fact_type_code = 'fact_date'
        or (normalized_date is null and date_precision_code is null)
    )
);

create index if not exists post_summary_source_fact_post_idx
    on post_summary_source_fact (post_id, fact_ordinal);

create index if not exists post_summary_source_fact_type_idx
    on post_summary_source_fact (fact_type_code, assertion_code, normalized_date);

commit;

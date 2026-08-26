-- ADR 0206: source-backed external-information relation target type.
alter table operations_case_fact
    add column if not exists relation_target_kind_code text;

alter table operations_case_fact
    drop constraint if exists operations_case_fact_relation_target_kind_check,
    add constraint operations_case_fact_relation_target_kind_check check (
        (fact_type_code = 'external_relation'
         and (relation_target_kind_code is null or relation_target_kind_code in
              ('order', 'project', 'sales', 'business_management')))
        or (fact_type_code <> 'external_relation' and relation_target_kind_code is null)
    ) not valid;

comment on column operations_case_fact.relation_target_kind_code is
    'Semantic target type supplied with cited external_relation evidence; null legacy rows are not projected as typed relations.';

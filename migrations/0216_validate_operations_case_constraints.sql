-- Validate ADR 0206 dashboard checks separately from their short NOT VALID installation.
alter table operations_case_fact
    validate constraint operations_case_fact_relation_target_kind_check;

alter table operations_case_milestone
    validate constraint operations_case_milestone_kind_type_check;

alter table operations_case_missing_milestone
    validate constraint operations_case_missing_milestone_kind_type_check;

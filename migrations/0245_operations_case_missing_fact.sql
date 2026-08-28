-- ADR 0206: unsupported required answers remain explicit without fabricated evidence.
create table if not exists operations_case_missing_fact (
    post_id uuid not null,
    case_kind_code text not null,
    fact_type_code text not null check (fact_type_code in ('order', 'specification_change', 'originating_order', 'sales_pool', 'discussion', 'counterparty', 'our_owner', 'decision', 'external_relation', 'issue_pattern', 'improvement_action')),
    primary key (post_id, case_kind_code, fact_type_code),
    foreign key (post_id, case_kind_code)
        references operations_case_classification(post_id, case_kind_code)
        on delete cascade
);

create index if not exists operations_case_missing_fact_kind_idx
    on operations_case_missing_fact (case_kind_code, fact_type_code, post_id);

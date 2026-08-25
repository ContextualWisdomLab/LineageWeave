-- Evidence-grounded operational case inference (ADR 0206). Replay-safe.
create table if not exists operations_case_analysis (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    orchestrator_session_id text not null,
    analyzed_at timestamptz not null default now()
);

create table if not exists operations_case_classification (
    post_id uuid not null references operations_case_analysis(post_id) on delete cascade,
    case_kind_code text not null check (case_kind_code in ('claim_investigation', 'rebid_handover', 'external_information', 'repeat_issue')),
    summary_text text not null check (btrim(summary_text) <> ''),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    primary key (post_id, case_kind_code)
);

create table if not exists operations_case_fact (
    post_id uuid not null,
    case_kind_code text not null,
    fact_ordinal integer not null check (fact_ordinal >= 0),
    fact_type_code text not null check (fact_type_code in ('order', 'specification_change', 'originating_order', 'sales_pool', 'discussion', 'counterparty', 'our_owner', 'decision', 'external_relation', 'issue_pattern', 'improvement_action')),
    value_text text not null check (btrim(value_text) <> ''),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    primary key (post_id, case_kind_code, fact_ordinal),
    foreign key (post_id, case_kind_code)
        references operations_case_classification(post_id, case_kind_code)
        on delete cascade
);

create index if not exists operations_case_classification_kind_post_idx
    on operations_case_classification (case_kind_code, post_id);

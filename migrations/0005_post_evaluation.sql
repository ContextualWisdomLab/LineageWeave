-- ADR 0003 slice 2: one IRT response per post per rubric criterion.
-- Scores come only from fast_mlsirm.LLMJudgeResult.to_irt_row(); this
-- table stores that row, it does not invent a second scoring pipeline.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('evaluation_criterion', 'general_sentiment_positive', 'Constructive stance', 0),
    ('evaluation_criterion', 'general_sentiment_negative', 'Negative stance', 1),
    ('evaluation_criterion', 'sales_lead_specificity', 'Sales-lead specificity', 2)
on conflict (lookup_code) do nothing;

create table if not exists post_evaluation_response (
    post_id uuid not null references source_post (post_id),
    criterion_code text not null references common_lookup_value (lookup_code),
    rubric_version text not null,
    response_category integer not null,
    judged_at timestamptz not null default now(),
    primary key (post_id, criterion_code, rubric_version)
);

create index if not exists post_evaluation_response_post_idx
    on post_evaluation_response (post_id);

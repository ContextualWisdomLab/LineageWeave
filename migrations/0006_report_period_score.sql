-- ADR 0003 slice 3: one calibrated period score per grouping.
-- Numbers come only from lineageweave.period_report.calibrate_period_report
-- (fast_mlsirm fit_polytomous + FIPC + EAP).

create table if not exists report_period_score (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    selected_model text not null,
    mean_theta numeric not null,
    mean_theta_sd numeric not null,
    post_count integer not null,
    item_count integer not null,
    fit_loglik numeric not null,
    fit_converged boolean not null,
    calibration_score numeric not null,
    computed_at timestamptz not null default now(),
    primary key (grouping_kind, grouping_key, period_code, rubric_version),
    check (grouping_kind in ('process_unit', 'corporate_entity', 'thread_group'))
);

create table if not exists report_member_score (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    post_id uuid not null references source_post (post_id),
    theta_eap numeric not null,
    theta_sd numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, post_id),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

create index if not exists report_member_score_post_idx on report_member_score (post_id);

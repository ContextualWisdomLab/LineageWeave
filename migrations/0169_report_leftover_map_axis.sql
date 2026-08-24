-- ADR 0148: persist leftover-map axis share (Gabriel inertia of residual
-- SVD axes 1 and 2). CREATE IF NOT EXISTS so a volume that already ran
-- 0001 still upgrades. Report-level 3NF; cascade with the period score.

create table if not exists report_leftover_map_axis (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    axis_index integer not null,
    leftover_singular_value numeric not null,
    leftover_share numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, axis_index),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (axis_index in (1, 2)),
    check (leftover_singular_value >= 0),
    check (leftover_share >= 0 and leftover_share <= 1)
);

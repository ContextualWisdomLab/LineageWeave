-- ADR 0017: persist closest/farthest leftover post–criterion pairs after
-- IRT main effects. CREATE IF NOT EXISTS so a volume that already ran
-- 0001 still upgrades.

create table if not exists report_leftover_pair (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    pair_kind text not null,
    post_id uuid not null references source_post (post_id),
    criterion_code text not null references common_lookup_value (lookup_code),
    leftover_distance numeric not null,
    leftover_residual numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, pair_kind),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (pair_kind in ('closest', 'farthest')),
    check (leftover_distance >= 0)
);

create index if not exists report_leftover_pair_post_idx on report_leftover_pair (post_id);

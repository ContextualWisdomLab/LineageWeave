-- ADR 0202: persist leftover complete-case coverage (map used N of M
-- scored posts). CREATE IF NOT EXISTS so a volume that already ran
-- 0001 still upgrades. Incomplete rows stay excluded; missing cells
-- are never stored as zero.

create table if not exists report_leftover_map_coverage (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    map_post_count integer not null,
    scored_post_count integer not null,
    map_item_count integer not null,
    scored_item_count integer not null,
    incomplete_post_count integer not null,
    incomplete_item_count integer not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (map_post_count >= 0),
    check (scored_post_count >= map_post_count),
    check (map_item_count >= 0),
    check (scored_item_count >= map_item_count),
    check (incomplete_post_count = scored_post_count - map_post_count),
    check (incomplete_item_count = scored_item_count - map_item_count)
);

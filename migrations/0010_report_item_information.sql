-- ADR 0003 slice 6: persist CAT item-information ranking on the shared
-- bank. CREATE IF NOT EXISTS so a volume that already ran 0001 still
-- upgrades.

create table if not exists report_item_information (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    item_code text not null,
    item_rank integer not null,
    information numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, item_code),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (item_rank >= 1)
);

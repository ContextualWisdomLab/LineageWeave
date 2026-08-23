-- ADR 0017: persist closest/farthest leftover post–criterion pairs after
-- IRT main effects. CREATE IF NOT EXISTS so a volume that already ran
-- 0001 still upgrades. Composite FKs are added below so an existing
-- table from an earlier 0012 still gains member/item integrity.

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
    leftover_map_rank integer not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, pair_kind),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (pair_kind in ('closest', 'farthest')),
    check (leftover_distance >= 0),
    check (leftover_map_rank >= 0)
);

create index if not exists report_leftover_pair_post_idx on report_leftover_pair (post_id);

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_member_score_fk'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_member_score_fk
            foreign key (grouping_kind, grouping_key, period_code, rubric_version, post_id)
            references report_member_score (
                grouping_kind, grouping_key, period_code, rubric_version, post_id
            )
            on delete cascade;
    end if;
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_item_information_fk'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_item_information_fk
            foreign key (grouping_kind, grouping_key, period_code, rubric_version, criterion_code)
            references report_item_information (
                grouping_kind, grouping_key, period_code, rubric_version, item_code
            )
            on delete cascade;
    end if;
end $$;

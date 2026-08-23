-- ADR 0121: persist leftover interaction-map coordinates after IRT main
-- effects. CREATE IF NOT EXISTS so a volume that already ran 0001 still
-- upgrades. Composite FKs are added below so an existing table from an
-- earlier 0104 still gains member/item integrity.

create table if not exists report_leftover_map_person (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    post_id uuid not null references source_post (post_id),
    axis_one numeric not null,
    axis_two numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, post_id),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

create index if not exists report_leftover_map_person_post_idx
    on report_leftover_map_person (post_id);

create table if not exists report_leftover_map_item (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    criterion_code text not null references common_lookup_value (lookup_code),
    axis_one numeric not null,
    axis_two numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, criterion_code),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_map_person_member_score_fk'
    ) then
        alter table report_leftover_map_person
            add constraint leftover_map_person_member_score_fk
            foreign key (grouping_kind, grouping_key, period_code, rubric_version, post_id)
            references report_member_score (
                grouping_kind, grouping_key, period_code, rubric_version, post_id
            )
            on delete cascade;
    end if;
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_map_item_information_fk'
    ) then
        alter table report_leftover_map_item
            add constraint leftover_map_item_information_fk
            foreign key (grouping_kind, grouping_key, period_code, rubric_version, criterion_code)
            references report_item_information (
                grouping_kind, grouping_key, period_code, rubric_version, item_code
            )
            on delete cascade;
    end if;
end $$;

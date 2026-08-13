-- ADR 0003 slice 4: persist the item bank and FIPC link metadata so
-- later weeks score on the same metric. ADD COLUMN IF NOT EXISTS so a
-- volume that already ran 0006 still upgrades.

alter table report_period_score
    add column if not exists link_method text not null default 'free';

alter table report_period_score
    add column if not exists anchor_period_code text;

alter table report_period_score
    add column if not exists delta_mean_theta numeric;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'report_period_score_link_method_check'
    ) then
        alter table report_period_score
            add constraint report_period_score_link_method_check
            check (link_method in ('free', 'fipc'));
    end if;
end
$$;

create table if not exists report_item_parameter (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    item_code text not null,
    item_index integer not null,
    slope numeric not null,
    cat_params numeric[] not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, item_code),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

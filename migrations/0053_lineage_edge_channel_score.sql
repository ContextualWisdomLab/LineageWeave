-- Preserve the exact evidence used for each selected Event Lineage edge.
-- PostgreSQL is authoritative: one reconstruction run owns a normalized active
-- weight profile, each selected edge references that run, and each active
-- signal stores its score and exact contribution. Missing channels stay absent.

begin;

insert into common_lookup_value (
    lookup_category,
    lookup_code,
    lookup_label,
    display_order
) values
    ('lineage_channel', 'lineage_channel_temporal', 'Time proximity', 0),
    ('lineage_channel', 'lineage_channel_secondary_key', 'Secondary key', 1),
    ('lineage_channel', 'lineage_channel_text', 'Text similarity', 2),
    ('lineage_channel', 'lineage_channel_llm', 'LLM adjudication', 3)
on conflict (lookup_code) do nothing;

do $$
begin
    if exists (
        select 1
          from common_lookup_value
         where lookup_code in (
             'lineage_channel_temporal',
             'lineage_channel_secondary_key',
             'lineage_channel_text',
             'lineage_channel_llm'
         )
           and lookup_category <> 'lineage_channel'
    ) then
        raise exception 'lineage channel lookup code belongs to another category';
    end if;
end
$$;

create table if not exists lineage_reconstruction_run (
    lineage_reconstruction_run_id uuid primary key,
    reconstruction_version text not null,
    generated_at timestamptz not null default now(),
    constraint lineage_reconstruction_run_version_chk
        check (length(btrim(reconstruction_version)) > 0)
);

create table if not exists lineage_reconstruction_run_channel (
    lineage_reconstruction_run_id uuid not null
        references lineage_reconstruction_run (lineage_reconstruction_run_id)
        on delete cascade,
    channel_code text not null references common_lookup_value (lookup_code),
    channel_weight numeric not null,
    primary key (lineage_reconstruction_run_id, channel_code),
    constraint lineage_reconstruction_run_channel_code_chk check (
        channel_code in (
            'lineage_channel_temporal',
            'lineage_channel_secondary_key',
            'lineage_channel_text',
            'lineage_channel_llm'
        )
    ),
    constraint lineage_reconstruction_run_channel_weight_chk
        check (channel_weight > 0 and channel_weight <= 1)
);

alter table post_lineage_edge
    add column if not exists lineage_reconstruction_run_id uuid;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'post_lineage_edge'::regclass
           and conname = 'post_lineage_edge_reconstruction_run_fk'
    ) then
        alter table post_lineage_edge
            add constraint post_lineage_edge_reconstruction_run_fk
            foreign key (lineage_reconstruction_run_id)
            references lineage_reconstruction_run (lineage_reconstruction_run_id);
    end if;
end
$$;

create index if not exists post_lineage_edge_reconstruction_run_idx
    on post_lineage_edge (lineage_reconstruction_run_id)
    where lineage_reconstruction_run_id is not null;

create table if not exists lineage_edge_channel_score (
    parent_post_id uuid not null,
    child_post_id uuid not null,
    channel_code text not null references common_lookup_value (lookup_code),
    channel_score numeric not null,
    channel_contribution numeric not null,
    created_at timestamptz not null default now(),
    primary key (parent_post_id, child_post_id, channel_code),
    foreign key (parent_post_id, child_post_id)
        references post_lineage_edge (parent_post_id, child_post_id)
        on delete cascade,
    constraint lineage_edge_channel_score_code_chk check (
        channel_code in (
            'lineage_channel_temporal',
            'lineage_channel_secondary_key',
            'lineage_channel_text',
            'lineage_channel_llm'
        )
    ),
    constraint lineage_edge_channel_score_value_chk
        check (channel_score >= 0 and channel_score <= 1),
    constraint lineage_edge_channel_contribution_value_chk
        check (channel_contribution >= 0 and channel_contribution <= 1)
);

-- A development database may have applied an earlier draft of this unmerged
-- migration that lacked contribution. Preserve no ambiguous derived value:
-- add the column, remove only those draft evidence rows, and require an
-- explicit reconstruction to repopulate them.
alter table lineage_edge_channel_score
    add column if not exists channel_contribution numeric;
delete from lineage_edge_channel_score where channel_contribution is null;
alter table lineage_edge_channel_score
    alter column channel_contribution set not null;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'lineage_edge_channel_score'::regclass
           and conname = 'lineage_edge_channel_contribution_value_chk'
    ) then
        alter table lineage_edge_channel_score
            add constraint lineage_edge_channel_contribution_value_chk
            check (channel_contribution >= 0 and channel_contribution <= 1);
    end if;
end
$$;

create index if not exists lineage_edge_channel_score_channel_idx
    on lineage_edge_channel_score (channel_code, parent_post_id, child_post_id);

comment on table lineage_reconstruction_run is
    'Version and generated-at authority for one explicit Event Lineage reconstruction.';
comment on table lineage_reconstruction_run_channel is
    'Normalized active channel weights actually used by one reconstruction run.';
comment on table lineage_edge_channel_score is
    'Exact score and contribution for an active signal on a selected post_lineage_edge. Absence means unavailable, never zero.';

commit;

-- ADR 0172: persist Event Lineage channel evidence beside each fused edge.
-- lookup_code is globally unique, so signal codes are prefixed.
-- Migration 0174 uses CREATE IF NOT EXISTS / ON CONFLICT for idempotent replay.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('lineage_signal', 'lineage_signal_temporal', 'Temporal proximity', 0),
    ('lineage_signal', 'lineage_signal_secondary_key', 'Secondary key match', 1),
    ('lineage_signal', 'lineage_signal_text', 'Text similarity', 2),
    ('lineage_signal', 'lineage_signal_llm', 'LLM adjudication', 3)
on conflict (lookup_code) do nothing;

create table if not exists event_lineage_rebuild (
    rebuild_lock boolean primary key default true check (rebuild_lock),
    reconstruction_version text not null,
    generated_at timestamptz not null,
    min_fused_score numeric(8,6) not null,
    candidate_window integer not null,
    check (min_fused_score >= 0 and min_fused_score <= 1),
    check (candidate_window >= 1)
);

comment on table event_lineage_rebuild is
    'Singleton identity of the live Event Lineage rebuild; replaced atomically.';

create table if not exists event_lineage_rebuild_channel (
    rebuild_lock boolean not null default true
        references event_lineage_rebuild (rebuild_lock) on delete cascade,
    signal_code text not null references common_lookup_value (lookup_code),
    signal_weight numeric(8,6) not null,
    primary key (rebuild_lock, signal_code),
    check (signal_weight > 0 and signal_weight <= 1)
);

comment on table event_lineage_rebuild_channel is
    'Normalized active channel weights used by the live Event Lineage rebuild.';

create table if not exists post_lineage_edge_signal (
    parent_post_id uuid not null,
    child_post_id uuid not null,
    signal_code text not null references common_lookup_value (lookup_code),
    signal_score numeric(8,6) not null,
    signal_weight numeric(8,6) not null,
    signal_contribution numeric(8,6) not null,
    primary key (parent_post_id, child_post_id, signal_code),
    foreign key (parent_post_id, child_post_id)
        references post_lineage_edge (parent_post_id, child_post_id)
        on delete cascade,
    check (signal_score >= 0 and signal_score <= 1),
    check (signal_weight > 0 and signal_weight <= 1),
    check (signal_contribution >= 0 and signal_contribution <= 1)
);

comment on table post_lineage_edge_signal is
    'Per-channel score, active weight, and contribution for one reconstructed lineage edge.';

do $migration$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'event_lineage_rebuild_channel_signal_code_check'
          and conrelid = 'event_lineage_rebuild_channel'::regclass
    ) then
        alter table event_lineage_rebuild_channel
            add constraint event_lineage_rebuild_channel_signal_code_check
            check (signal_code in (
                'lineage_signal_temporal',
                'lineage_signal_secondary_key',
                'lineage_signal_text',
                'lineage_signal_llm'
            ));
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'post_lineage_edge_signal_code_check'
          and conrelid = 'post_lineage_edge_signal'::regclass
    ) then
        alter table post_lineage_edge_signal
            add constraint post_lineage_edge_signal_code_check
            check (signal_code in (
                'lineage_signal_temporal',
                'lineage_signal_secondary_key',
                'lineage_signal_text',
                'lineage_signal_llm'
            ));
    end if;
end;
$migration$;

create index if not exists post_lineage_edge_signal_child_idx
    on post_lineage_edge_signal (child_post_id, parent_post_id);

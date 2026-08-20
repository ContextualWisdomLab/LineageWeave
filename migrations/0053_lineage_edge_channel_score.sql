-- Preserve the independent evidence channels computed for each selected
-- Event Lineage edge. `post_lineage_edge.fused_score` remains the selected
-- edge's aggregate ranking value; these child rows explain that value and do
-- not promote the reconstructed relation to an authoritative or causal fact.

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

create table if not exists lineage_edge_channel_score (
    parent_post_id uuid not null,
    child_post_id uuid not null,
    channel_code text not null references common_lookup_value (lookup_code),
    channel_score numeric not null,
    created_at timestamptz not null default now(),
    primary key (parent_post_id, child_post_id, channel_code),
    foreign key (parent_post_id, child_post_id)
        references post_lineage_edge (parent_post_id, child_post_id)
        on delete cascade,
    check (
        channel_code in (
            'lineage_channel_temporal',
            'lineage_channel_secondary_key',
            'lineage_channel_text',
            'lineage_channel_llm'
        )
    ),
    check (channel_score >= 0 and channel_score <= 1)
);

create index if not exists lineage_edge_channel_score_channel_idx
    on lineage_edge_channel_score (channel_code, parent_post_id, child_post_id);

comment on table lineage_edge_channel_score is
    'Exact reconstruction channel evidence for a selected post_lineage_edge. '
    'Absence means the channel was unavailable; it must not be read as zero.';

commit;

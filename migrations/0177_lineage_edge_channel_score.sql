-- Per-channel score breakdown for each Event Lineage edge (ADR 0191): a
-- single fused_score number tells a reader that reconstruct() linked two
-- posts, never WHY -- whether the link came from temporal proximity, a
-- shared secondary key, text/embedding similarity, or an llm judgment.
-- Persisting each channel's contribution lets the DAG show that evidence
-- inline instead of collapsing it into one opaque number.
create table if not exists post_lineage_edge_channel_score (
    parent_post_id uuid not null,
    child_post_id uuid not null,
    channel_code text not null check (channel_code in (
        'temporal', 'secondary_key', 'text', 'llm'
    )),
    channel_score numeric(5,4) not null check (channel_score >= 0 and channel_score <= 1),
    primary key (parent_post_id, child_post_id, channel_code),
    foreign key (parent_post_id, child_post_id)
        references post_lineage_edge (parent_post_id, child_post_id)
        on delete cascade
);

create index if not exists post_lineage_edge_channel_score_edge_idx
    on post_lineage_edge_channel_score (parent_post_id, child_post_id);

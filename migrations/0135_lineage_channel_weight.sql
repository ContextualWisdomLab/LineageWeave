-- ADR 0145: reserve an integrity- and provenance-bearing persistence contract.
-- No anchor method is currently authorized, so application code activates no
-- stored vector.

alter table source_post
    add column if not exists source_thread_group_key text,
    add column if not exists source_secondary_grouping_key text;

comment on column source_post.source_thread_group_key is
    'Raw caller-mapped source thread field; preserved separately from derived reconstruction grouping.';
comment on column source_post.source_secondary_grouping_key is
    'Raw caller-mapped source secondary-group field; preserved separately from derived reconstruction evidence.';

create table if not exists lineage_channel_weight (
    channel_code text primary key,
    weight_value double precision not null,
    estimation_run_id uuid not null,
    estimation_method_code text not null,
    estimator_version text not null,
    anchor_method_code text not null,
    source_snapshot_sha256 text not null,
    sample_pair_count bigint not null,
    knowledge_cutoff timestamptz not null,
    estimated_at timestamptz not null default now(),
    constraint lineage_channel_code_check
        check (channel_code in ('temporal', 'secondary_key', 'text', 'llm')),
    constraint lineage_weight_value_check
        check (weight_value > 0 and weight_value <= 1),
    constraint lineage_estimation_method_check
        check (btrim(estimation_method_code) <> ''),
    constraint lineage_estimator_version_check
        check (btrim(estimator_version) <> ''),
    constraint lineage_anchor_method_check
        check (btrim(anchor_method_code) <> ''),
    constraint lineage_sample_pair_count_check
        check (sample_pair_count >= 200),
    constraint lineage_source_snapshot_check
        check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    constraint lineage_knowledge_cutoff_check
        check (knowledge_cutoff <= estimated_at)
);

-- ADR 0145: lineage channel-fusion weights become estimated, persisted,
-- provenance-bearing quantities instead of hand-picked constants.
-- One row per channel; rebuild_lineage uses the set only when it exactly
-- matches the active channel set (no partial mixing).

create table if not exists lineage_channel_weight (
    channel_code text primary key,
    weight_value double precision not null,
    estimation_method_code text not null,
    sample_pair_count bigint not null,
    estimated_at timestamptz not null default now()
);

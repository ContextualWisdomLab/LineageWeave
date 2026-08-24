-- ADR 0145 §5: one persisted weight set per active channel combination.
-- The corpus-wide rebuild runs the three deterministic channels while a
-- scoped analysis run with an adjudication client runs four; a single
-- flat set cannot serve both without the exact-match rule failing one
-- of them closed (product reconstruction never falls back to
-- hand-picked constants). Existing rows are the deterministic set.

alter table lineage_channel_weight
    add column if not exists channel_set_code text not null default 'channel_set_deterministic';

alter table lineage_channel_weight
    drop constraint if exists lineage_channel_weight_pkey;

alter table lineage_channel_weight
    add primary key (channel_set_code, channel_code);

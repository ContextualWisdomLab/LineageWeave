-- ADR 0200 point 4: union of the two lines' lineage_channel_weight schemas.
--
-- Predecessors this must upgrade from, idempotently (ADR 0166 replay window):
--   * main's 0135: primary key (channel_code) + per-run provenance columns.
--   * the customer-master line's 0135+0136: primary key
--     (channel_set_code, channel_code), no provenance columns.
-- Target: primary key (channel_set_code, channel_code) -- one persisted set
-- per active-channel combination -- carrying main's full provenance contract.
--
-- Rows persisted before the provenance contract existed are unverifiable
-- estimates; they are deleted rather than backfilled with invented
-- provenance (the loader refuses them either way, and re-running
-- scripts/estimate_channel_weights.py is the operator's next action).

do $$
begin
    if not exists (
        select from information_schema.columns
        where table_name = 'lineage_channel_weight'
          and column_name = 'estimation_run_id'
    ) then
        delete from lineage_channel_weight;
    end if;
end $$;

alter table lineage_channel_weight
    add column if not exists channel_set_code text not null
        default 'channel_set_deterministic',
    add column if not exists estimation_run_id uuid not null,
    add column if not exists estimation_method_code text not null,
    add column if not exists estimator_version text not null,
    add column if not exists anchor_method_code text not null,
    add column if not exists source_snapshot_sha256 text not null,
    add column if not exists sample_pair_count bigint not null,
    add column if not exists knowledge_cutoff timestamptz not null,
    add column if not exists estimated_at timestamptz not null default now();

do $$
declare
    primary_key_columns text;
begin
    select string_agg(a.attname, ',' order by array_position(x.conkey, a.attnum))
      into primary_key_columns
      from pg_constraint x
      join pg_attribute a
        on a.attrelid = x.conrelid and a.attnum = any(x.conkey)
     where x.conrelid = 'lineage_channel_weight'::regclass
       and x.contype = 'p';
    if primary_key_columns is distinct from 'channel_set_code,channel_code' then
        execute 'alter table lineage_channel_weight drop constraint if exists lineage_channel_weight_pkey';
        execute 'alter table lineage_channel_weight add primary key (channel_set_code, channel_code)';
    end if;
end $$;

alter table lineage_channel_weight
    drop constraint if exists lineage_channel_set_code_check;
alter table lineage_channel_weight
    add constraint lineage_channel_set_code_check
        check (channel_set_code in ('channel_set_deterministic', 'channel_set_with_llm'));

-- Re-assert main's 0135 integrity constraints for databases coming from the
-- customer-master predecessor, which never had them.
do $$
begin
    if not exists (
        select from pg_constraint
        where conrelid = 'lineage_channel_weight'::regclass
          and conname = 'lineage_channel_code_check'
    ) then
        alter table lineage_channel_weight
            add constraint lineage_channel_code_check
                check (channel_code in ('temporal', 'secondary_key', 'text', 'llm')),
            add constraint lineage_weight_value_check
                check (weight_value > 0 and weight_value <= 1),
            add constraint lineage_estimation_method_check
                check (btrim(estimation_method_code) <> ''),
            add constraint lineage_estimator_version_check
                check (btrim(estimator_version) <> ''),
            add constraint lineage_anchor_method_check
                check (btrim(anchor_method_code) <> ''),
            add constraint lineage_sample_pair_count_check
                check (sample_pair_count >= 200),
            add constraint lineage_source_snapshot_check
                check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
            add constraint lineage_knowledge_cutoff_check
                check (knowledge_cutoff <= estimated_at);
    end if;
end $$;

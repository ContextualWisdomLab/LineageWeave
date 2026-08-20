-- Persist only a provider-authoritative completed TEPP envelope.
-- LineageWeave never computes or substitutes a psychometric measurement.
create table if not exists analysis_run_tepp_result (
    analysis_run_id uuid primary key references analysis_run(analysis_run_id) on delete cascade,
    remote_run_id text not null check (btrim(remote_run_id) <> ''),
    result_json jsonb not null,
    result_sha256 text not null check (result_sha256 ~ '^[0-9a-f]{64}$'),
    persisted_at timestamptz not null default now()
);

create index if not exists analysis_run_tepp_result_remote_idx
    on analysis_run_tepp_result (remote_run_id);

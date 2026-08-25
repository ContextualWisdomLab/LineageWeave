-- Persist only a provider-authoritative completed TEPP topic-lineage
-- envelope (TRSL-TM topic identity + CHRONOS/TDT event-intelligence
-- status, ADR 0132). LineageWeave never computes or substitutes a topic
-- model or event prediction; result_json stores TEPP's versioned envelope
-- verbatim until its schema stabilizes into dedicated columns.
create table if not exists analysis_run_topic_lineage_result (
    analysis_run_id uuid primary key references analysis_run(analysis_run_id) on delete cascade,
    remote_run_id text not null check (btrim(remote_run_id) <> ''),
    result_json jsonb not null,
    result_sha256 text not null check (result_sha256 ~ '^[0-9a-f]{64}$'),
    persisted_at timestamptz not null default now()
);

create index if not exists analysis_run_topic_lineage_result_remote_idx
    on analysis_run_topic_lineage_result (remote_run_id);

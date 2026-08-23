-- Persist only a provider-authoritative completed TEPP topic-lineage
-- `tepp.trsl_topic_lineage.v1` envelope (ADR 0147). LineageWeave never
-- computes or substitutes a topic model; result_json retains the exact
-- digest-bound TEPP artifact envelope.
create table if not exists analysis_run_topic_lineage_result (
    analysis_run_id uuid primary key references analysis_run(analysis_run_id) on delete cascade,
    remote_run_id text not null check (btrim(remote_run_id) <> ''),
    result_json jsonb not null,
    result_sha256 text not null check (result_sha256 ~ '^[0-9a-f]{64}$'),
    persisted_at timestamptz not null default now()
);

create index if not exists analysis_run_topic_lineage_result_remote_idx
    on analysis_run_topic_lineage_result (remote_run_id);

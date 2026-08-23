-- Persist TEPP AnalysisRunAccepted as transport evidence (ADR 0157).
-- This is not a measurement: no result JSON and no Succeeded stamp.
-- Completed envelopes stay on analysis_run_tepp_result (migration 0027).
create table if not exists analysis_run_tepp_accepted_receipt (
    analysis_run_id uuid primary key
        references analysis_run(analysis_run_id) on delete cascade,
    remote_run_id text not null unique check (btrim(remote_run_id) <> ''),
    request_sha256 text not null check (request_sha256 ~ '^[0-9a-f]{64}$'),
    receipt_sha256 text not null check (receipt_sha256 ~ '^[0-9a-f]{64}$'),
    accepted_status_code text not null
        check (accepted_status_code in ('accepted', 'queued', 'running')),
    model_contract_version text not null check (btrim(model_contract_version) <> ''),
    snapshot_id text not null check (btrim(snapshot_id) <> ''),
    knowledge_cutoff timestamptz not null,
    received_at timestamptz not null default clock_timestamp()
);

create index if not exists analysis_run_tepp_accepted_receipt_received_idx
    on analysis_run_tepp_accepted_receipt (received_at);

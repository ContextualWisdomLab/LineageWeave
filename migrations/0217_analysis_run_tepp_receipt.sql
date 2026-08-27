-- TEPP acceptance is durable transport evidence, never a measurement result.
create table if not exists analysis_run_tepp_receipt (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id) on delete cascade,
    remote_run_id text not null unique check (btrim(remote_run_id) <> ''),
    request_sha256 text not null check (request_sha256 ~ '^[0-9a-f]{64}$'),
    receipt_sha256 text not null check (receipt_sha256 ~ '^[0-9a-f]{64}$'),
    accepted_status_code text not null
        check (accepted_status_code = 'accepted'),
    received_at timestamptz not null default clock_timestamp()
);

create index if not exists analysis_run_tepp_receipt_received_idx
    on analysis_run_tepp_receipt (received_at);

-- Migration 0271 / ADR 0244: successful receipt for derived Voice analysis.
create table if not exists post_voice_classification_analysis (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null
        check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    orchestrator_model_receipt text not null
        check (btrim(orchestrator_model_receipt) <> ''),
    assertion_count integer not null check (assertion_count >= 0),
    analyzed_at timestamptz not null default clock_timestamp()
);

create index if not exists post_voice_classification_analysis_digest_idx
    on post_voice_classification_analysis (source_body_sha256, post_id);

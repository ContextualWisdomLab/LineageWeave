-- ADR 0200 point 5: durable, resumable llm pair judging.
--
-- Bulk synchronous provider calls are banned (operator directive,
-- 2026-08-24): the operator submits the sampled pairs as ONE
-- contextual-orchestrator batch routing job (its Valkey-backed registry
-- survives orchestrator restarts) and each returned score persists here
-- as it is collected, so a killed collection loses nothing and the fit
-- runs only over a complete run.

create table if not exists lineage_weight_estimation_run (
    estimation_run_id uuid primary key,
    channel_set_code text not null,
    run_status_code text not null,
    batch_job_id text not null,
    source_snapshot_sha256 text not null,
    knowledge_cutoff timestamptz not null,
    sampled_pair_count bigint not null,
    judged_pair_count bigint not null default 0,
    requested_at timestamptz not null default now(),
    completed_at timestamptz,
    constraint estimation_run_status_check
        check (run_status_code in
            ('run_submitted', 'run_collecting', 'run_fitted', 'run_failed')),
    constraint estimation_run_set_check
        check (channel_set_code in
            ('channel_set_deterministic', 'channel_set_with_llm')),
    constraint estimation_run_snapshot_check
        check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    constraint estimation_run_pair_count_check
        check (sampled_pair_count > 0),
    constraint estimation_run_judged_count_check
        check (judged_pair_count >= 0 and judged_pair_count <= sampled_pair_count)
);

create table if not exists lineage_pair_judgment (
    estimation_run_id uuid not null
        references lineage_weight_estimation_run (estimation_run_id)
        on delete cascade,
    pair_ordinal bigint not null,
    group_ordinal bigint not null,
    candidate_label text not null,
    record_label text not null,
    temporal_score double precision not null,
    secondary_key_score double precision not null,
    text_score double precision not null,
    llm_score double precision,
    judged_at timestamptz,
    primary key (estimation_run_id, pair_ordinal),
    constraint pair_judgment_scores_check
        check (
            temporal_score between 0 and 1
            and secondary_key_score between 0 and 1
            and text_score between 0 and 1
            and (llm_score is null or llm_score between 0 and 1)
        ),
    constraint pair_judgment_judged_check
        check ((llm_score is null) = (judged_at is null))
);

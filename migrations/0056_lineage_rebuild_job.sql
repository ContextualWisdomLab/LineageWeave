-- ADR 0107: durable lineage rebuild jobs. PostgreSQL is truth; Valkey is
-- only a wake-up. No post body or fabricated LLM score is stored.

insert into common_lookup_value (
    lookup_category, lookup_code, lookup_label, display_order
) values
    ('lineage_rebuild_status', 'lineage_rebuild_queued', 'Queued', 0),
    ('lineage_rebuild_status', 'lineage_rebuild_running', 'Running', 1),
    ('lineage_rebuild_status', 'lineage_rebuild_succeeded', 'Succeeded', 2),
    ('lineage_rebuild_status', 'lineage_rebuild_failed', 'Failed', 3),
    ('lineage_rebuild_status', 'lineage_rebuild_cancelled', 'Cancelled', 4),
    ('lineage_llm_channel_status', 'lineage_llm_requested', 'LLM channel requested', 0),
    ('lineage_llm_channel_status', 'lineage_llm_available', 'LLM channel available', 1),
    ('lineage_llm_channel_status', 'lineage_llm_completed', 'LLM channel completed', 2),
    ('lineage_llm_channel_status', 'lineage_llm_skipped', 'LLM channel skipped', 3),
    ('lineage_llm_channel_status', 'lineage_llm_failed', 'LLM channel failed', 4),
    ('lineage_llm_channel_status', 'lineage_llm_unavailable', 'LLM channel unavailable', 5)
on conflict (lookup_code) do nothing;

create table if not exists lineage_rebuild_job (
    lineage_rebuild_job_id uuid primary key default gen_random_uuid(),
    requested_by_account_id uuid not null
        references user_account (user_account_id),
    source_snapshot_sha256 text not null
        check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    knowledge_cutoff timestamptz not null,
    pair_estimate integer not null check (pair_estimate >= 0),
    pair_limit integer not null check (pair_limit > 0),
    llm_channel_requested boolean not null,
    llm_channel_status_code text not null
        references common_lookup_value (lookup_code),
    status_code text not null
        references common_lookup_value (lookup_code),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    edge_count integer check (edge_count is null or edge_count >= 0),
    result_sha256 text check (
        result_sha256 is null or result_sha256 ~ '^[0-9a-f]{64}$'
    ),
    failure_code text,
    queued_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now(),
    constraint lineage_rebuild_job_status_check
        check (
            status_code in (
                'lineage_rebuild_queued',
                'lineage_rebuild_running',
                'lineage_rebuild_succeeded',
                'lineage_rebuild_failed',
                'lineage_rebuild_cancelled'
            )
        ),
    constraint lineage_rebuild_job_llm_status_check
        check (
            llm_channel_status_code in (
                'lineage_llm_requested',
                'lineage_llm_available',
                'lineage_llm_completed',
                'lineage_llm_skipped',
                'lineage_llm_failed',
                'lineage_llm_unavailable'
            )
        ),
    constraint lineage_rebuild_job_time_check
        check (queued_at <= updated_at)
);

comment on table lineage_rebuild_job is
    'One durable Event Lineage rebuild. PostgreSQL is the source of truth; '
    'Valkey is only a wake-up. Never stores a post body or a fused LLM score.';

create unique index if not exists lineage_rebuild_job_active_snapshot_idx
    on lineage_rebuild_job (source_snapshot_sha256, llm_channel_requested)
    where status_code in ('lineage_rebuild_queued', 'lineage_rebuild_running');

create index if not exists lineage_rebuild_job_status_idx
    on lineage_rebuild_job (status_code, queued_at);

create table if not exists lineage_rebuild_job_status_event (
    lineage_rebuild_job_id uuid not null
        references lineage_rebuild_job (lineage_rebuild_job_id) on delete cascade,
    status_ordinal integer not null check (status_ordinal >= 0),
    status_code text not null
        references common_lookup_value (lookup_code),
    llm_channel_status_code text not null
        references common_lookup_value (lookup_code),
    occurred_at timestamptz not null default now(),
    failure_code text,
    detail_text text,
    primary key (lineage_rebuild_job_id, status_ordinal),
    constraint lineage_rebuild_event_status_check
        check (
            status_code in (
                'lineage_rebuild_queued',
                'lineage_rebuild_running',
                'lineage_rebuild_succeeded',
                'lineage_rebuild_failed',
                'lineage_rebuild_cancelled'
            )
        ),
    constraint lineage_rebuild_event_llm_status_check
        check (
            llm_channel_status_code in (
                'lineage_llm_requested',
                'lineage_llm_available',
                'lineage_llm_completed',
                'lineage_llm_skipped',
                'lineage_llm_failed',
                'lineage_llm_unavailable'
            )
        )
);

comment on table lineage_rebuild_job_status_event is
    'Append-only rebuild lifecycle events. Absence of an LLM channel stays '
    'unavailable or skipped; it is never stored as a zero score.';

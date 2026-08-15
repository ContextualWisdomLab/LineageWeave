-- Normalized, aggregate-only provenance for Milestone 2 analysis runs.
--
-- The source SQL, DSN, raw post content, image bytes, provider credentials,
-- and private source identifiers remain operator-owned and are never stored in
-- these tables. Only opaque profile keys, immutable digests, bounded
-- configuration, aggregate counts, service identifiers, and status events are
-- persisted. This keeps actual-data acceptance evidence outside public source
-- control while making runtime derivations auditable.

begin;

insert into common_lookup_value (
    lookup_category, lookup_code, lookup_label, display_order
) values
    ('analysis_source_kind', 'postgresql_query_profile', 'PostgreSQL query profile', 10),
    ('analysis_run_status', 'analysis_run_running', 'Running', 10),
    ('analysis_run_status', 'analysis_run_succeeded', 'Succeeded', 20),
    ('analysis_run_status', 'analysis_run_failed', 'Failed', 30),
    ('analysis_run_event_type', 'analysis_run_started_event', 'Analysis run started', 10),
    ('analysis_run_event_type', 'analysis_run_completed_event', 'Analysis run completed', 20),
    ('analysis_run_event_type', 'analysis_run_failed_event', 'Analysis run failed', 30),
    ('analysis_service_kind', 'analysis_service_tepp', 'TEPP', 10),
    ('analysis_service_kind', 'analysis_service_orchestrator', 'Contextual Orchestrator', 20),
    ('analysis_service_kind', 'analysis_service_fast_mlsirm', 'fast-mlsirm', 30),
    ('analysis_service_status', 'analysis_service_running', 'Service run running', 10),
    ('analysis_service_status', 'analysis_service_succeeded', 'Service run succeeded', 20),
    ('analysis_service_status', 'analysis_service_failed', 'Service run failed', 30),
    ('analysis_artifact_kind', 'analysis_aggregate_manifest', 'Aggregate acceptance manifest', 10),
    ('analysis_artifact_kind', 'analysis_reproducibility_manifest', 'Reproducibility manifest', 20),
    ('analysis_artifact_kind', 'analysis_browser_evidence', 'Browser acceptance evidence', 30);

create table analysis_source_profile (
    source_profile_id uuid primary key default uuid_generate_v4(),
    source_profile_key text not null
        check (source_profile_key ~ '^[a-z0-9][a-z0-9._-]{0,127}$'),
    profile_revision integer not null check (profile_revision >= 1),
    source_kind_code text not null references common_lookup_value (lookup_code)
        check (source_kind_code in ('postgresql_query_profile')),
    query_digest_sha256 text not null
        check (query_digest_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    unique (source_profile_key, profile_revision)
);

comment on table analysis_source_profile is
    'Opaque, immutable source-query revision. The SQL and DSN remain outside '
    'the product database; only a profile key and exact query digest are stored.';

create table analysis_source_snapshot (
    source_snapshot_id uuid primary key default uuid_generate_v4(),
    source_profile_id uuid not null
        references analysis_source_profile (source_profile_id),
    source_digest_sha256 text not null
        check (source_digest_sha256 ~ '^[0-9a-f]{64}$'),
    knowledge_cutoff timestamptz not null,
    maximum_available_time timestamptz not null,
    row_count bigint not null check (row_count >= 0),
    document_count bigint not null check (
        document_count >= 0 and document_count <= row_count
    ),
    thread_count bigint not null check (
        thread_count >= 0 and thread_count <= document_count
    ),
    observed_at timestamptz not null default now(),
    check (maximum_available_time <= knowledge_cutoff),
    check (observed_at >= maximum_available_time),
    unique (source_profile_id, source_digest_sha256, knowledge_cutoff)
);

comment on table analysis_source_snapshot is
    'Aggregate-only immutable snapshot evidence. maximum_available_time must '
    'not exceed knowledge_cutoff, preventing future-information leakage.';

create table analysis_run_record (
    analysis_run_id uuid primary key default uuid_generate_v4(),
    source_snapshot_id uuid not null
        references analysis_source_snapshot (source_snapshot_id),
    requested_by_account_id uuid not null
        references user_account (user_account_id),
    run_status_code text not null references common_lookup_value (lookup_code)
        check (run_status_code in (
            'analysis_run_running',
            'analysis_run_succeeded',
            'analysis_run_failed'
        )),
    idempotency_key text not null unique
        check (length(btrim(idempotency_key)) between 1 and 255),
    request_digest_sha256 text not null
        check (request_digest_sha256 ~ '^[0-9a-f]{64}$'),
    started_at timestamptz not null,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    check (completed_at is null or completed_at >= started_at),
    check (
        (run_status_code = 'analysis_run_running' and completed_at is null)
        or (
            run_status_code in ('analysis_run_succeeded', 'analysis_run_failed')
            and completed_at is not null
        )
    ),
    check (created_at >= started_at)
);

create index analysis_run_started_idx
    on analysis_run_record (started_at desc, analysis_run_id desc);

create table analysis_run_configuration (
    analysis_run_id uuid primary key
        references analysis_run_record (analysis_run_id) on delete cascade,
    row_limit bigint not null check (row_limit >= 0),
    write_reports boolean not null,
    inspect_inline_images boolean not null,
    validate_runtime_schema boolean not null,
    model_contract_version text not null,
    output_profile text not null,
    check (length(btrim(model_contract_version)) between 1 and 128),
    check (length(btrim(output_profile)) between 1 and 128)
);

create table analysis_run_event (
    analysis_run_event_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null
        references analysis_run_record (analysis_run_id) on delete cascade,
    event_type_code text not null references common_lookup_value (lookup_code)
        check (event_type_code in (
            'analysis_run_started_event',
            'analysis_run_completed_event',
            'analysis_run_failed_event'
        )),
    actor_account_id uuid not null references user_account (user_account_id),
    occurred_at timestamptz not null,
    recorded_at timestamptz not null default now(),
    payload_digest_sha256 text not null
        check (payload_digest_sha256 ~ '^[0-9a-f]{64}$'),
    check (recorded_at >= occurred_at),
    unique (
        analysis_run_id, event_type_code, occurred_at, payload_digest_sha256
    )
);

create index analysis_run_event_run_idx
    on analysis_run_event (analysis_run_id, occurred_at);

create table analysis_service_run (
    analysis_service_run_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null
        references analysis_run_record (analysis_run_id) on delete cascade,
    service_kind_code text not null references common_lookup_value (lookup_code)
        check (service_kind_code in (
            'analysis_service_tepp',
            'analysis_service_orchestrator',
            'analysis_service_fast_mlsirm'
        )),
    service_status_code text not null references common_lookup_value (lookup_code)
        check (service_status_code in (
            'analysis_service_running',
            'analysis_service_succeeded',
            'analysis_service_failed'
        )),
    remote_run_identifier text not null,
    idempotency_key text not null,
    request_digest_sha256 text not null
        check (request_digest_sha256 ~ '^[0-9a-f]{64}$'),
    retryable boolean not null default false,
    started_at timestamptz not null,
    completed_at timestamptz,
    check (length(btrim(remote_run_identifier)) between 1 and 255),
    check (length(btrim(idempotency_key)) between 1 and 255),
    check (completed_at is null or completed_at >= started_at),
    check (
        (service_status_code = 'analysis_service_running' and completed_at is null)
        or (
            service_status_code in (
                'analysis_service_succeeded', 'analysis_service_failed'
            )
            and completed_at is not null
        )
    ),
    unique (service_kind_code, remote_run_identifier),
    unique (service_kind_code, idempotency_key)
);

create index analysis_service_run_parent_idx
    on analysis_service_run (analysis_run_id, started_at);

create table analysis_artifact_record (
    analysis_artifact_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null
        references analysis_run_record (analysis_run_id) on delete cascade,
    artifact_kind_code text not null references common_lookup_value (lookup_code)
        check (artifact_kind_code in (
            'analysis_aggregate_manifest',
            'analysis_reproducibility_manifest',
            'analysis_browser_evidence'
        )),
    artifact_reference_uri text not null,
    content_digest_sha256 text not null
        check (content_digest_sha256 ~ '^[0-9a-f]{64}$'),
    byte_count bigint not null check (byte_count >= 0),
    created_at timestamptz not null default now(),
    check (length(btrim(artifact_reference_uri)) between 1 and 2048),
    unique (analysis_run_id, artifact_kind_code, content_digest_sha256)
);

create index analysis_artifact_run_idx
    on analysis_artifact_record (analysis_run_id, created_at);

commit;

-- Digest-bound temporal evidence admitted only for existing Event Lineage edges.
create table if not exists project_journey_temporal_artifact (
    analysis_run_id uuid primary key references analysis_run_tepp_result(analysis_run_id) on delete cascade,
    remote_run_id text not null,
    schema_version text not null check (schema_version = 'tepp.tdt_chronos_interval_consistency.v1'),
    snapshot_id text not null check (btrim(snapshot_id) <> ''),
    input_digest_sha256 text not null check (input_digest_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_digest_sha256 text not null unique check (artifact_digest_sha256 ~ '^[0-9a-f]{64}$'),
    admitted_at timestamptz not null default clock_timestamp(),
    unique (analysis_run_id, remote_run_id)
);

create table if not exists project_journey_temporal_relation (
    analysis_run_id uuid not null references project_journey_temporal_artifact(analysis_run_id) on delete cascade,
    left_post_id uuid not null references source_post(post_id) on delete cascade,
    right_post_id uuid not null references source_post(post_id) on delete cascade,
    observed boolean not null,
    primary key (analysis_run_id, left_post_id, right_post_id),
    foreign key (left_post_id, right_post_id)
        references post_lineage_edge(parent_post_id, child_post_id) on delete cascade,
    check (left_post_id <> right_post_id)
);

create table if not exists project_journey_temporal_relation_kind (
    analysis_run_id uuid not null,
    left_post_id uuid not null,
    right_post_id uuid not null,
    relation_code text not null check (relation_code in (
        'before', 'after', 'meets', 'met_by', 'overlaps', 'overlapped_by',
        'starts', 'started_by', 'during', 'contains', 'finishes', 'finished_by', 'equals'
    )),
    relation_ordinal smallint not null check (relation_ordinal between 0 and 12),
    primary key (analysis_run_id, left_post_id, right_post_id, relation_code),
    unique (analysis_run_id, left_post_id, right_post_id, relation_ordinal),
    foreign key (analysis_run_id, left_post_id, right_post_id)
        references project_journey_temporal_relation(analysis_run_id, left_post_id, right_post_id)
        on delete cascade
);

create table if not exists project_journey_temporal_support (
    analysis_run_id uuid not null,
    left_post_id uuid not null,
    right_post_id uuid not null,
    assertion_ordinal integer not null check (assertion_ordinal >= 0),
    primary key (analysis_run_id, left_post_id, right_post_id, assertion_ordinal),
    foreign key (analysis_run_id, left_post_id, right_post_id)
        references project_journey_temporal_relation(analysis_run_id, left_post_id, right_post_id)
        on delete cascade
);

create index if not exists project_journey_temporal_relation_right_idx
    on project_journey_temporal_relation (right_post_id, left_post_id, analysis_run_id);

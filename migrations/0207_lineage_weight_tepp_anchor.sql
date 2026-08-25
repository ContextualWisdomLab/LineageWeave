-- ADR 0205: normalized projection of a completed, persisted TEPP criterion anchor.
create table if not exists lineage_weight_tepp_anchor (
    estimation_run_id uuid primary key,
    tepp_analysis_run_id uuid not null unique
        references analysis_run_tepp_result (analysis_run_id) on delete restrict,
    anchor_kind_code text not null
        check (anchor_kind_code = 'lineage_pair_criterion'),
    anchor_contract_version integer not null
        check (anchor_contract_version = 1),
    source_snapshot_sha256 text not null
        check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    knowledge_cutoff timestamptz not null,
    criterion_validity_status_code text not null
        check (criterion_validity_status_code = 'accepted'),
    validated_pair_count bigint not null check (validated_pair_count > 0),
    persisted_at timestamptz not null default now()
);

comment on table lineage_weight_tepp_anchor is
    'Fail-closed TEPP criterion-validity projection for one fast-mlsirm lineage-weight run; authoritative result remains analysis_run_tepp_result.result_json.';


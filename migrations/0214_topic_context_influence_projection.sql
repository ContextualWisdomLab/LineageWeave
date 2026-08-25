-- ADR 0210: normalized TEPP topic and fast-mlsirm influence projection.
-- LineageWeave stores accepted producer evidence; it performs no estimator math.

create table if not exists topic_model_run (
    topic_model_run_id uuid primary key default uuid_generate_v4(),
    analysis_run_id uuid not null unique references analysis_run (analysis_run_id),
    tepp_run_id text not null unique check (length(btrim(tepp_run_id)) between 1 and 256),
    tepp_snapshot_id text not null check (length(btrim(tepp_snapshot_id)) between 1 and 256),
    tepp_schema_version text not null check (tepp_schema_version = 'tepp.topic_context_posterior.v1'),
    tepp_model_contract_version text not null check (length(btrim(tepp_model_contract_version)) between 1 and 256),
    tepp_artifact_sha256 text not null unique check (tepp_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    reported_source_snapshot_sha256 text not null check (reported_source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    reported_knowledge_cutoff timestamptz not null,
    posterior_draw_set_id text not null check (length(btrim(posterior_draw_set_id)) between 1 and 256),
    posterior_draw_count integer not null check (posterior_draw_count > 0),
    topic_count integer not null check (topic_count >= 2),
    inference_status_code text not null check (inference_status_code = 'posterior_topic_coordinates_not_importance'),
    accepted_at timestamptz not null default now()
);

create table if not exists topic_definition (
    topic_model_run_id uuid not null references topic_model_run (topic_model_run_id) on delete cascade,
    topic_index integer not null check (topic_index >= 0),
    primary key (topic_model_run_id, topic_index)
);

create table if not exists topic_activity_interval (
    topic_model_run_id uuid not null,
    topic_index integer not null,
    valid_from timestamptz not null,
    valid_to timestamptz not null,
    state_code text not null check (state_code in ('active', 'dormant', 'reactivated')),
    primary key (topic_model_run_id, topic_index, valid_from),
    foreign key (topic_model_run_id, topic_index)
        references topic_definition (topic_model_run_id, topic_index) on delete cascade,
    check (valid_from < valid_to)
);

create table if not exists topic_lineage_relation (
    topic_model_run_id uuid not null,
    relation_ordinal integer not null check (relation_ordinal >= 0),
    event_code text not null check (event_code in ('birth', 'split', 'merge', 'retirement')),
    source_topic_index integer not null,
    target_topic_index integer,
    event_time timestamptz not null,
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (topic_model_run_id, relation_ordinal),
    foreign key (topic_model_run_id, source_topic_index)
        references topic_definition (topic_model_run_id, topic_index) on delete cascade,
    foreign key (topic_model_run_id, target_topic_index)
        references topic_definition (topic_model_run_id, topic_index) on delete cascade,
    check (
        (event_code in ('split', 'merge') and target_topic_index is not null)
        or (event_code in ('birth', 'retirement') and target_topic_index is null)
    )
);

create table if not exists topic_context_definition (
    topic_model_run_id uuid not null references topic_model_run (topic_model_run_id) on delete cascade,
    dimension_code text not null check (dimension_code in ('business_unit', 'process_unit', 'team', 'person')),
    context_id text not null check (length(btrim(context_id)) between 1 and 256),
    context_label text not null check (length(btrim(context_label)) between 1 and 512),
    primary key (topic_model_run_id, dimension_code, context_id)
);

create table if not exists topic_context_membership (
    topic_model_run_id uuid not null references topic_model_run (topic_model_run_id) on delete cascade,
    topic_context_membership_id uuid not null default uuid_generate_v4(),
    source_post_id uuid not null references source_post (post_id) on delete restrict,
    dimension_code text not null check (dimension_code in ('business_unit', 'process_unit', 'team', 'person')),
    context_id text not null check (length(btrim(context_id)) between 1 and 256),
    membership_weight double precision not null check (
        membership_weight > 0 and membership_weight < 'Infinity'::double precision
    ),
    valid_from timestamptz not null,
    valid_to timestamptz not null,
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (topic_model_run_id, topic_context_membership_id),
    unique (topic_model_run_id, source_post_id, dimension_code, context_id, valid_from),
    foreign key (topic_model_run_id, dimension_code, context_id)
        references topic_context_definition (topic_model_run_id, dimension_code, context_id)
        on delete cascade,
    check (valid_from < valid_to)
);

create table if not exists topic_influence_run (
    topic_model_run_id uuid not null references topic_model_run (topic_model_run_id) on delete cascade,
    topic_influence_run_id uuid not null default uuid_generate_v4(),
    fast_mlsirm_schema_version text not null check (fast_mlsirm_schema_version = 'fast_mlsirm.topic_context_influence.v1'),
    fast_mlsirm_version text not null check (length(btrim(fast_mlsirm_version)) between 1 and 128),
    fast_mlsirm_code_revision text not null check (fast_mlsirm_code_revision ~ '^(?:[0-9a-f]{40}|[0-9a-f]{64})$'),
    fast_mlsirm_artifact_sha256 text not null unique check (fast_mlsirm_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    reported_tepp_run_id text not null,
    reported_snapshot_sha256 text not null check (reported_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    reported_knowledge_cutoff timestamptz not null,
    membership_fingerprint_sha256 text not null check (membership_fingerprint_sha256 ~ '^[0-9a-f]{64}$'),
    compute_backend_code text not null check (compute_backend_code in ('rust_cpu', 'rust_gpu')),
    precision_code text not null check (precision_code in ('f64', 'f32')),
    posterior_draw_coverage integer not null check (posterior_draw_coverage > 0),
    convergence_status_code text not null check (convergence_status_code = 'converged'),
    identification_status_code text not null check (identification_status_code = 'identified'),
    parity_status_code text not null check (parity_status_code = 'passed'),
    accepted_at timestamptz not null default now(),
    primary key (topic_model_run_id, topic_influence_run_id)
);

create table if not exists topic_post_context_influence (
    topic_model_run_id uuid not null,
    topic_influence_run_id uuid not null,
    topic_context_membership_id uuid not null,
    topic_index integer not null,
    influence_value double precision not null check (
        influence_value >= 0 and influence_value < 'Infinity'::double precision
    ),
    uncertainty_method_code text not null check (length(btrim(uncertainty_method_code)) between 1 and 128),
    uncertainty_lower_value double precision not null check (
        uncertainty_lower_value >= 0 and uncertainty_lower_value < 'Infinity'::double precision
    ),
    uncertainty_upper_value double precision not null check (
        uncertainty_upper_value >= uncertainty_lower_value
        and uncertainty_upper_value < 'Infinity'::double precision
    ),
    diagnostic_status_code text not null check (diagnostic_status_code = 'accepted'),
    primary key (
        topic_model_run_id,
        topic_influence_run_id,
        topic_context_membership_id,
        topic_index
    ),
    foreign key (topic_model_run_id, topic_influence_run_id)
        references topic_influence_run (topic_model_run_id, topic_influence_run_id) on delete cascade,
    foreign key (topic_model_run_id, topic_context_membership_id)
        references topic_context_membership (topic_model_run_id, topic_context_membership_id) on delete cascade,
    foreign key (topic_model_run_id, topic_index)
        references topic_definition (topic_model_run_id, topic_index) on delete cascade
);

create index if not exists topic_activity_interval_time_idx
    on topic_activity_interval (valid_from, valid_to, topic_model_run_id, topic_index);
create index if not exists topic_context_membership_post_time_idx
    on topic_context_membership (source_post_id, valid_from, valid_to, topic_model_run_id);
create index if not exists topic_post_context_influence_read_idx
    on topic_post_context_influence (topic_model_run_id, topic_index, influence_value desc);

create or replace function validate_topic_model_run_binding()
returns trigger
language plpgsql
as $$
declare
    canonical_snapshot_sha256 text;
    canonical_knowledge_cutoff timestamptz;
    canonical_run_kind_code text;
begin
    select snapshot.snapshot_sha256, run.knowledge_cutoff, run.run_kind_code
      into canonical_snapshot_sha256, canonical_knowledge_cutoff, canonical_run_kind_code
      from analysis_run run
      join analysis_source_snapshot snapshot
        on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
     where run.analysis_run_id = new.analysis_run_id;

    if canonical_run_kind_code is distinct from 'analysis_run_topic_lineage'
       or new.reported_source_snapshot_sha256 is distinct from canonical_snapshot_sha256
       or new.reported_knowledge_cutoff is distinct from canonical_knowledge_cutoff then
        raise exception 'topic_model_run_provenance_binding_mismatch';
    end if;
    return new;
end
$$;

drop trigger if exists topic_model_run_binding_check on topic_model_run;
create trigger topic_model_run_binding_check
before insert or update on topic_model_run
for each row execute function validate_topic_model_run_binding();

create or replace function validate_topic_influence_run_binding()
returns trigger
language plpgsql
as $$
declare
    canonical_tepp_run_id text;
    canonical_snapshot_sha256 text;
    canonical_knowledge_cutoff timestamptz;
    canonical_draw_count integer;
begin
    select model.tepp_run_id, snapshot.snapshot_sha256, run.knowledge_cutoff,
           model.posterior_draw_count
      into canonical_tepp_run_id, canonical_snapshot_sha256,
           canonical_knowledge_cutoff, canonical_draw_count
      from topic_model_run model
      join analysis_run run on run.analysis_run_id = model.analysis_run_id
      join analysis_source_snapshot snapshot
        on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
     where model.topic_model_run_id = new.topic_model_run_id;

    if new.reported_tepp_run_id is distinct from canonical_tepp_run_id
       or new.reported_snapshot_sha256 is distinct from canonical_snapshot_sha256
       or new.reported_knowledge_cutoff is distinct from canonical_knowledge_cutoff
       or new.posterior_draw_coverage is distinct from canonical_draw_count then
        raise exception 'topic_influence_provenance_binding_mismatch';
    end if;
    return new;
end
$$;

drop trigger if exists topic_influence_run_binding_check on topic_influence_run;
create trigger topic_influence_run_binding_check
before insert or update on topic_influence_run
for each row execute function validate_topic_influence_run_binding();

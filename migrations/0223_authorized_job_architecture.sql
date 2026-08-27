-- ADR 0263: authorized, source-preserving job-family/job-series snapshots.

begin;

create table if not exists job_architecture_source (
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    source_system_code text not null,
    source_snapshot_code text not null,
    source_name text not null,
    source_artifact_url text not null,
    source_artifact_sha256 text not null,
    source_row_count bigint not null,
    imported_at timestamptz not null default now(),
    primary key (corporate_entity_id, source_system_code, source_snapshot_code),
    constraint job_architecture_source_system_check
        check (source_system_code ~ '^[a-z][a-z0-9_]{0,62}$'),
    constraint job_architecture_snapshot_check check (btrim(source_snapshot_code) <> ''),
    constraint job_architecture_source_name_check check (btrim(source_name) <> ''),
    constraint job_architecture_source_digest_check
        check (source_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    constraint job_architecture_source_rows_check check (source_row_count > 0)
);

create table if not exists job_architecture_node (
    corporate_entity_id uuid not null,
    source_system_code text not null,
    source_snapshot_code text not null,
    job_architecture_code text not null,
    job_architecture_kind_code text not null,
    job_architecture_name text not null,
    job_architecture_description text,
    valid_from date,
    valid_to date,
    primary key (
        corporate_entity_id, source_system_code, source_snapshot_code,
        job_architecture_code
    ),
    constraint job_architecture_node_source_fkey
        foreign key (corporate_entity_id, source_system_code, source_snapshot_code)
        references job_architecture_source
            (corporate_entity_id, source_system_code, source_snapshot_code),
    constraint job_architecture_node_code_check check (btrim(job_architecture_code) <> ''),
    constraint job_architecture_node_kind_check
        check (job_architecture_kind_code in ('job_family', 'job_series')),
    constraint job_architecture_node_name_check check (btrim(job_architecture_name) <> ''),
    constraint job_architecture_node_validity_check
        check (valid_from is null or valid_to is null or valid_from <= valid_to)
);

create table if not exists job_architecture_hierarchy_edge (
    corporate_entity_id uuid not null,
    source_system_code text not null,
    source_snapshot_code text not null,
    broader_job_architecture_code text not null,
    narrower_job_architecture_code text not null,
    source_relation_code text not null,
    primary key (
        corporate_entity_id, source_system_code, source_snapshot_code,
        broader_job_architecture_code, narrower_job_architecture_code
    ),
    constraint job_architecture_hierarchy_source_fkey
        foreign key (corporate_entity_id, source_system_code, source_snapshot_code)
        references job_architecture_source
            (corporate_entity_id, source_system_code, source_snapshot_code),
    constraint job_architecture_hierarchy_broader_fkey
        foreign key (
            corporate_entity_id, source_system_code, source_snapshot_code,
            broader_job_architecture_code
        ) references job_architecture_node (
            corporate_entity_id, source_system_code, source_snapshot_code,
            job_architecture_code
        ),
    constraint job_architecture_hierarchy_narrower_fkey
        foreign key (
            corporate_entity_id, source_system_code, source_snapshot_code,
            narrower_job_architecture_code
        ) references job_architecture_node (
            corporate_entity_id, source_system_code, source_snapshot_code,
            job_architecture_code
        ),
    constraint job_architecture_hierarchy_distinct_check
        check (broader_job_architecture_code <> narrower_job_architecture_code),
    constraint job_architecture_hierarchy_relation_check
        check (btrim(source_relation_code) <> '')
);

create table if not exists job_architecture_occupation_binding (
    corporate_entity_id uuid not null,
    source_system_code text not null,
    source_snapshot_code text not null,
    job_architecture_code text not null,
    occupation_scheme_iri text not null,
    occupation_scheme_version text not null,
    occupation_code text not null,
    source_relation_code text not null,
    primary key (
        corporate_entity_id, source_system_code, source_snapshot_code,
        job_architecture_code, occupation_scheme_iri,
        occupation_scheme_version, occupation_code
    ),
    constraint job_architecture_binding_node_fkey
        foreign key (
            corporate_entity_id, source_system_code, source_snapshot_code,
            job_architecture_code
        ) references job_architecture_node (
            corporate_entity_id, source_system_code, source_snapshot_code,
            job_architecture_code
        ),
    constraint job_architecture_binding_scheme_check
        check (occupation_scheme_iri ~ '^https?://'),
    constraint job_architecture_binding_version_check
        check (btrim(occupation_scheme_version) <> ''),
    constraint job_architecture_binding_code_check check (btrim(occupation_code) <> ''),
    constraint job_architecture_binding_relation_check
        check (btrim(source_relation_code) <> '')
);

create index if not exists job_architecture_node_lookup_idx
    on job_architecture_node
    (corporate_entity_id, job_architecture_kind_code, job_architecture_name);

create index if not exists job_architecture_binding_occupation_idx
    on job_architecture_occupation_binding
    (occupation_scheme_iri, occupation_scheme_version, occupation_code);

create or replace function reject_job_architecture_mutation()
returns trigger
language plpgsql
as $$
begin
    raise check_violation using message = 'job architecture source evidence is immutable';
end;
$$;

do $$
declare
    table_name text;
begin
    foreach table_name in array array[
        'job_architecture_source',
        'job_architecture_node',
        'job_architecture_hierarchy_edge',
        'job_architecture_occupation_binding'
    ] loop
        execute format('drop trigger if exists job_architecture_reject_mutation on %I', table_name);
        execute format(
            'create trigger job_architecture_reject_mutation before update or delete on %I for each row execute function reject_job_architecture_mutation()',
            table_name
        );
        execute format('drop trigger if exists job_architecture_reject_truncate on %I', table_name);
        execute format(
            'create trigger job_architecture_reject_truncate before truncate on %I for each statement execute function reject_job_architecture_mutation()',
            table_name
        );
    end loop;
end;
$$;

commit;

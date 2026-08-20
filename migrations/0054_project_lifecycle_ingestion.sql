begin;

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('project_event_type', 'project_event_order', 'Project order or contract award', 0),
    ('project_event_type', 'project_event_spec_change', 'Project specification change', 1),
    ('project_event_type', 'project_event_delivery', 'Project delivery completion', 2),
    ('project_event_type', 'project_event_voc', 'Project voice of customer', 3),
    ('project_event_type', 'project_event_rebid', 'Project tender or rebid', 4),
    ('project_record_state', 'project_record_active', 'Active project source record', 0),
    ('project_record_state', 'project_record_withdrawn', 'Withdrawn project source record', 1),
    ('project_relation_type', 'project_relation_precedes', 'Explicitly precedes', 0),
    ('project_relation_type', 'project_relation_related', 'Explicitly related', 1),
    ('prov_agent_type', 'prov_person', 'Person', 0),
    ('prov_agent_type', 'prov_organization', 'Organization', 1),
    ('prov_agent_type', 'prov_team', 'Team', 2)
on conflict (lookup_code) do nothing;

create table if not exists project_identity (
    project_identity_id uuid primary key default uuid_generate_v4(),
    project_key text not null unique,
    project_name text not null
);

create table if not exists project_source_system (
    project_source_system_id uuid primary key default uuid_generate_v4(),
    source_system_code text not null unique,
    source_system_name text not null
);

create table if not exists project_event_mapping (
    project_event_mapping_id uuid primary key default uuid_generate_v4(),
    project_source_system_id uuid not null references project_source_system,
    mapping_version text not null,
    source_event_code text not null,
    project_event_type_code text not null references common_lookup_value (lookup_code),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (project_source_system_id, mapping_version, source_event_code)
);

create table if not exists project_source_record (
    project_source_record_id uuid primary key default uuid_generate_v4(),
    project_source_system_id uuid not null references project_source_system,
    source_record_key text not null,
    project_identity_id uuid not null references project_identity,
    project_event_mapping_id uuid not null references project_event_mapping,
    lifecycle_state_code text not null references common_lookup_value (lookup_code),
    record_digest text not null,
    imported_by text not null,
    imported_at timestamptz not null default now(),
    unique (project_source_system_id, source_record_key)
);

create table if not exists project_lifecycle_event (
    project_lifecycle_event_id uuid primary key default uuid_generate_v4(),
    project_source_record_id uuid not null unique references project_source_record on delete cascade,
    project_event_type_code text not null references common_lookup_value (lookup_code),
    event_started_at timestamptz not null,
    event_ended_at timestamptz,
    event_digest text not null,
    created_at timestamptz not null default now(),
    check (event_ended_at is null or event_ended_at >= event_started_at)
);

create table if not exists project_event_evidence (
    project_lifecycle_event_id uuid not null references project_lifecycle_event on delete cascade,
    evidence_post_id uuid not null references source_post (post_id),
    evidence_role_code text not null,
    primary key (project_lifecycle_event_id, evidence_post_id, evidence_role_code),
    unique (project_lifecycle_event_id, evidence_role_code)
);

create table if not exists project_actor (
    project_actor_id uuid primary key default uuid_generate_v4(),
    project_identity_id uuid not null references project_identity,
    actor_type_code text not null references common_lookup_value (lookup_code),
    actor_key text not null,
    actor_name text not null,
    unique (project_identity_id, actor_type_code, actor_key)
);

create table if not exists project_event_responsibility (
    owner_source_record_id uuid not null references project_source_record on delete cascade,
    project_lifecycle_event_id uuid not null references project_lifecycle_event on delete cascade,
    project_actor_id uuid not null references project_actor,
    responsibility_text text not null,
    evidence_post_id uuid not null references source_post (post_id),
    primary key (project_lifecycle_event_id, project_actor_id, responsibility_text),
    unique (owner_source_record_id, project_lifecycle_event_id, project_actor_id, responsibility_text)
);

create table if not exists project_event_relation (
    project_event_relation_id uuid primary key default uuid_generate_v4(),
    owner_source_record_id uuid not null references project_source_record on delete cascade,
    source_lifecycle_event_id uuid not null references project_lifecycle_event on delete cascade,
    target_lifecycle_event_id uuid not null references project_lifecycle_event,
    relation_type_code text not null references common_lookup_value (lookup_code),
    evidence_post_id uuid not null references source_post (post_id),
    unique (owner_source_record_id, source_lifecycle_event_id, target_lifecycle_event_id, relation_type_code),
    check (source_lifecycle_event_id <> target_lifecycle_event_id)
);

create table if not exists project_lifecycle_audit (
    project_lifecycle_audit_id uuid primary key default uuid_generate_v4(),
    project_source_record_id uuid not null references project_source_record,
    action_code text not null,
    actor_key text not null,
    mapping_version text not null,
    before_digest text,
    after_digest text,
    occurred_at timestamptz not null default now()
);

create index if not exists project_source_record_identity_idx
    on project_source_record (project_identity_id, lifecycle_state_code);
create index if not exists project_lifecycle_event_time_idx
    on project_lifecycle_event (event_started_at, project_event_type_code);
create index if not exists project_event_relation_target_idx
    on project_event_relation (target_lifecycle_event_id);

comment on table project_event_mapping is
    'Versioned explicit source-code mapping; title/body classification is not authoritative.';
comment on table project_source_record is
    'Source-owned idempotency and withdrawal boundary for lifecycle projections.';
comment on table project_lifecycle_audit is
    'Aggregate audit digests for administrative lifecycle upsert and withdrawal actions.';

commit;

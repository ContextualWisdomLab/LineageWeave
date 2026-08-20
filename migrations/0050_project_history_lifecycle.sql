begin;

-- Evidence-bound project lifecycle read model (ADR 0100).
-- PostgreSQL remains authoritative; OWL-Time/PROV-O are projections.

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('project_event_type', 'project_event_order', 'Order awarded', 0),
    ('project_event_type', 'project_event_spec_change', 'Specification changed', 1),
    ('project_event_type', 'project_event_delivery', 'Delivered', 2),
    ('project_event_type', 'project_event_voc', 'VOC received', 3),
    ('project_event_type', 'project_event_rebid', 'Rebid', 4),
    ('project_relation_type', 'project_relation_follows', 'Follows', 0),
    ('project_relation_type', 'project_relation_related_to', 'Related to', 1),
    ('project_relation_type', 'project_relation_revises', 'Revises', 2),
    ('project_responsibility_role', 'project_role_sales', 'Sales', 0),
    ('project_responsibility_role', 'project_role_project_manager', 'Project manager', 1),
    ('project_responsibility_role', 'project_role_service', 'Service', 2)
on conflict (lookup_code) do update set
    lookup_category = excluded.lookup_category,
    lookup_label = excluded.lookup_label,
    display_order = excluded.display_order;

create table if not exists project_history_project (
    project_key text primary key check (btrim(project_key) <> ''),
    project_name text not null check (btrim(project_name) <> ''),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists project_history_event (
    project_history_event_id uuid primary key default uuid_generate_v4(),
    project_key text not null
        references project_history_project (project_key) on delete cascade,
    event_type_code text not null references common_lookup_value (lookup_code),
    event_title text not null check (btrim(event_title) <> ''),
    event_start_at timestamptz not null,
    event_end_at timestamptz,
    evidence_post_id uuid not null references source_post (post_id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (project_key, evidence_post_id, event_type_code, event_start_at),
    check (event_end_at is null or event_end_at >= event_start_at)
);

create index if not exists project_history_event_project_time_idx
    on project_history_event (project_key, event_start_at, project_history_event_id);
create index if not exists project_history_event_evidence_post_idx
    on project_history_event (evidence_post_id);

create table if not exists project_event_relation (
    source_project_history_event_id uuid not null
        references project_history_event (project_history_event_id) on delete cascade,
    target_project_history_event_id uuid not null
        references project_history_event (project_history_event_id) on delete cascade,
    relation_type_code text not null references common_lookup_value (lookup_code),
    evidence_post_id uuid not null references source_post (post_id) on delete cascade,
    relation_confidence numeric(4,3),
    created_at timestamptz not null default now(),
    primary key (
        source_project_history_event_id,
        target_project_history_event_id,
        relation_type_code
    ),
    check (source_project_history_event_id <> target_project_history_event_id),
    check (
        relation_confidence is null
        or (relation_confidence >= 0 and relation_confidence <= 1)
    )
);

create index if not exists project_event_relation_target_idx
    on project_event_relation (target_project_history_event_id);
create index if not exists project_event_relation_evidence_post_idx
    on project_event_relation (evidence_post_id);

create or replace function validate_project_event_relation_scope()
returns trigger
language plpgsql
as $$
declare
    source_project_key text;
    target_project_key text;
begin
    select project_key into source_project_key
      from project_history_event
     where project_history_event_id = new.source_project_history_event_id;

    select project_key into target_project_key
      from project_history_event
     where project_history_event_id = new.target_project_history_event_id;

    if source_project_key is distinct from target_project_key then
        raise exception 'project event relations must stay within one project';
    end if;
    return new;
end
$$;

drop trigger if exists project_event_relation_scope_check
    on project_event_relation;
create constraint trigger project_event_relation_scope_check
after insert or update on project_event_relation
deferrable initially immediate
for each row execute function validate_project_event_relation_scope();

create table if not exists project_responsibility_assignment (
    project_responsibility_assignment_id uuid primary key default uuid_generate_v4(),
    project_key text not null
        references project_history_project (project_key) on delete cascade,
    cataloged_person_id uuid not null references cataloged_person (person_id),
    responsibility_role_code text not null references common_lookup_value (lookup_code),
    valid_from timestamptz not null,
    valid_to timestamptz,
    evidence_post_id uuid not null references source_post (post_id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (
        project_key,
        cataloged_person_id,
        responsibility_role_code,
        valid_from
    ),
    check (valid_to is null or valid_to >= valid_from)
);

create index if not exists project_responsibility_project_time_idx
    on project_responsibility_assignment (
        project_key,
        valid_from,
        project_responsibility_assignment_id
    );
create index if not exists project_responsibility_evidence_post_idx
    on project_responsibility_assignment (evidence_post_id);

comment on table project_history_project is
    'Canonical project identity for the evidence-bound lifecycle read model.';
comment on table project_history_event is
    'Evidence-backed project lifecycle events, visible only when their source_post is authorized.';
comment on table project_event_relation is
    'Typed temporal or associative links between events in the same project; no causal claim is implied.';
comment on table project_responsibility_assignment is
    'Evidence-backed project responsibility intervals used to calculate visible handover gaps.';

commit;

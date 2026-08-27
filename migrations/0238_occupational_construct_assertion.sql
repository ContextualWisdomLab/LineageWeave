-- ADR 0249: versioned occupational constructs and evidence-unit assertions.
-- Replay-safe; numerical measurement remains outside LineageWeave.

create table if not exists occupational_construct_vocabulary (
    vocabulary_id uuid primary key default gen_random_uuid(),
    vocabulary_iri text not null check (btrim(vocabulary_iri) <> ''),
    version_label text not null check (btrim(version_label) <> ''),
    license_iri text not null check (btrim(license_iri) <> ''),
    attribution_text text not null check (btrim(attribution_text) <> ''),
    created_at timestamptz not null default now(),
    unique (vocabulary_iri, version_label)
);

create table if not exists occupational_construct (
    construct_id uuid primary key default gen_random_uuid(),
    vocabulary_id uuid not null references occupational_construct_vocabulary(vocabulary_id),
    construct_iri text not null check (btrim(construct_iri) <> ''),
    construct_family_code text not null check (construct_family_code in (
        'cognitive_ability',
        'work_style',
        'work_activity',
        'affective_reaction',
        'performance_behavior'
    )),
    preferred_label text not null check (btrim(preferred_label) <> ''),
    unique (vocabulary_id, construct_iri)
);

create table if not exists post_occupational_construct_assertion (
    assertion_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post(post_id) on delete cascade,
    post_content_unit_id uuid not null references post_content_unit(post_content_unit_id) on delete cascade,
    construct_id uuid not null references occupational_construct(construct_id),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    truth_status_code text not null references common_lookup_value(lookup_code) check (
        truth_status_code in (
            'truth_authoritative',
            'truth_observed',
            'truth_inferred',
            'truth_proposed',
            'truth_superseded',
            'truth_rejected'
        )
    ),
    extraction_method text not null check (btrim(extraction_method) <> ''),
    orchestrator_session_id text not null check (btrim(orchestrator_session_id) <> ''),
    generated_at timestamptz not null default now(),
    unique (post_id, post_content_unit_id, construct_id, extraction_method)
);

create or replace function validate_occupational_construct_evidence()
returns trigger
language plpgsql
as $$
declare
    unit_post_id uuid;
    selected_unit_text text;
begin
    select unit.post_id, unit.unit_text
      into unit_post_id, selected_unit_text
      from post_content_unit unit
     where unit.post_content_unit_id = new.post_content_unit_id;
    if unit_post_id is null or unit_post_id <> new.post_id then
        raise exception 'occupational construct evidence unit must belong to the assertion post';
    end if;
    if strpos(selected_unit_text, new.evidence_text) = 0 then
        raise exception 'occupational construct evidence must be verbatim unit text';
    end if;
    return new;
end;
$$;

drop trigger if exists occupational_construct_evidence_trigger
    on post_occupational_construct_assertion;
create trigger occupational_construct_evidence_trigger
before insert or update on post_occupational_construct_assertion
for each row execute function validate_occupational_construct_evidence();

create index if not exists occupational_construct_family_iri_idx
    on occupational_construct (construct_family_code, construct_iri);
create index if not exists post_occupational_construct_post_time_idx
    on post_occupational_construct_assertion (post_id, generated_at desc, assertion_id);
create index if not exists post_occupational_construct_construct_post_idx
    on post_occupational_construct_assertion (construct_id, post_id);

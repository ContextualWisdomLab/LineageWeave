-- ADR 0229: source-preserving, multi-membership voice taxonomy assertions.
create table if not exists post_voice_classification_assertion (
    classification_assertion_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post(post_id) on delete cascade,
    voice_concept_code text not null
        check (voice_concept_code in ('voc', 'vocc', 'voco', 'vom', 'vop')),
    assertion_status_code text not null
        check (assertion_status_code in ('source', 'derived')),
    evidence_span_start integer,
    evidence_span_end integer,
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    source_revision_digest text not null
        check (source_revision_digest ~ '^[0-9a-f]{64}$'),
    orchestrator_model_receipt text,
    valid_from timestamptz,
    valid_to timestamptz,
    recorded_at timestamptz not null default now(),
    supersedes_assertion_id uuid references post_voice_classification_assertion(classification_assertion_id),
    check ((evidence_span_start is null) = (evidence_span_end is null)),
    check (evidence_span_start is null or (evidence_span_start >= 0 and evidence_span_end > evidence_span_start)),
    check (valid_to is null or valid_from is null or valid_to >= valid_from),
    check (assertion_status_code = 'source' or (evidence_span_start is not null and btrim(orchestrator_model_receipt) <> ''))
);
create index if not exists post_voice_assertion_scope_idx
    on post_voice_classification_assertion (post_id, valid_from, voice_concept_code);
create unique index if not exists post_voice_assertion_idempotency_idx
    on post_voice_classification_assertion
    (post_id, assertion_status_code, voice_concept_code, source_revision_digest);

insert into post_voice_classification_assertion (
    post_id, voice_concept_code, assertion_status_code,
    evidence_sha256, source_revision_digest, valid_from
)
select post.post_id,
       lower(post.voc_type_code),
       'source',
       encode(sha256(convert_to(post.voc_type_code, 'UTF8')), 'hex'),
       encode(sha256(convert_to(coalesce(post.post_body, ''), 'UTF8')), 'hex'),
       coalesce(post.event_occurred_at, post.created_at)
  from source_post post
 where lower(post.voc_type_code) in ('voc', 'vocc', 'voco', 'vom', 'vop')
on conflict (post_id, assertion_status_code, voice_concept_code, source_revision_digest)
do nothing;

create table if not exists organization_voice_relationship_assertion (
    relationship_assertion_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post(post_id) on delete cascade,
    corporate_entity_id uuid not null references corporate_entity(corporate_entity_id),
    relationship_concept_code text not null
        check (relationship_concept_code in ('rel_voc', 'rel_vocc', 'rel_voco', 'rel_vom', 'rel_vop', 'rel_vos')),
    evidence_span_start integer not null check (evidence_span_start >= 0),
    evidence_span_end integer not null check (evidence_span_end > evidence_span_start),
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    source_revision_digest text not null
        check (source_revision_digest ~ '^[0-9a-f]{64}$'),
    orchestrator_model_receipt text not null check (btrim(orchestrator_model_receipt) <> ''),
    product_catalog_id uuid references product_catalog(product_catalog_id),
    valid_from timestamptz,
    valid_to timestamptz,
    recorded_at timestamptz not null default now(),
    supersedes_assertion_id uuid references organization_voice_relationship_assertion(relationship_assertion_id),
    check (valid_to is null or valid_from is null or valid_to >= valid_from)
);
create index if not exists organization_voice_assertion_scope_idx
    on organization_voice_relationship_assertion
    (corporate_entity_id, valid_from, relationship_concept_code, post_id);

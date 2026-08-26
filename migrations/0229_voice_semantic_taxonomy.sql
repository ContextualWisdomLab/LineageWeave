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
    check (valid_to is null or valid_from is null or valid_to >= valid_from)
);
do $migration$
begin
    if not exists (
        select 1 from pg_constraint
         where conrelid = 'post_voice_classification_assertion'::regclass
           and conname = 'post_voice_derived_receipt_check'
    ) then
        alter table post_voice_classification_assertion
            add constraint post_voice_derived_receipt_check check (
                assertion_status_code = 'source'
                or (
                    evidence_span_start is not null
                    and orchestrator_model_receipt is not null
                    and btrim(orchestrator_model_receipt) <> ''
                )
            );
    end if;
end
$migration$;
create index if not exists post_voice_assertion_scope_idx
    on post_voice_classification_assertion (post_id, valid_from, voice_concept_code);
drop index if exists post_voice_assertion_idempotency_idx;
create unique index post_voice_assertion_idempotency_idx
    on post_voice_classification_assertion
    (post_id, assertion_status_code, voice_concept_code, source_revision_digest)
    where valid_to is null;

insert into post_voice_classification_assertion (
    post_id, voice_concept_code, assertion_status_code,
    evidence_sha256, source_revision_digest
)
select post.post_id,
       lower(post.voc_type_code),
       'source',
       encode(sha256(convert_to(post.voc_type_code, 'UTF8')), 'hex'),
       encode(sha256(convert_to(coalesce(post.post_body, ''), 'UTF8')), 'hex')
  from source_post post
 where lower(post.voc_type_code) in ('voc', 'vocc', 'voco', 'vom', 'vop')
on conflict (post_id, assertion_status_code, voice_concept_code, source_revision_digest)
where valid_to is null
do nothing;

-- Source labels are recorded provenance, not future business-event claims.
-- Repair rows written by an earlier replay of this migration without changing
-- a separately sourced assertion that happens to share the post and concept.
update post_voice_classification_assertion assertion
   set valid_from = null
  from source_post post
 where assertion.post_id = post.post_id
   and assertion.assertion_status_code = 'source'
   and assertion.voice_concept_code = lower(post.voc_type_code)
   and assertion.evidence_sha256 =
       encode(sha256(convert_to(post.voc_type_code, 'UTF8')), 'hex')
   and assertion.source_revision_digest =
       encode(sha256(convert_to(coalesce(post.post_body, ''), 'UTF8')), 'hex')
   and assertion.valid_from is not null;

create or replace function reconcile_post_voice_source_assertion()
returns trigger
language plpgsql
as $function$
declare
    current_evidence_sha256 text;
    current_revision_digest text;
    matching_assertion_id uuid;
    prior_assertion_id uuid;
begin
    if lower(coalesce(new.voc_type_code, '')) not in
       ('voc', 'vocc', 'voco', 'vom', 'vop') then
        update post_voice_classification_assertion
           set valid_to = current_timestamp
         where post_id = new.post_id
           and assertion_status_code = 'source'
           and valid_to is null;
        return new;
    end if;

    current_evidence_sha256 :=
        encode(sha256(convert_to(new.voc_type_code, 'UTF8')), 'hex');
    current_revision_digest :=
        encode(sha256(convert_to(coalesce(new.post_body, ''), 'UTF8')), 'hex');

    select classification_assertion_id
      into matching_assertion_id
      from post_voice_classification_assertion
     where post_id = new.post_id
       and assertion_status_code = 'source'
       and voice_concept_code = lower(new.voc_type_code)
       and evidence_sha256 = current_evidence_sha256
       and source_revision_digest = current_revision_digest
       and valid_to is null
     order by recorded_at desc, classification_assertion_id
     limit 1;

    if matching_assertion_id is not null then
        update post_voice_classification_assertion
           set valid_to = current_timestamp
         where post_id = new.post_id
           and assertion_status_code = 'source'
           and valid_to is null
           and classification_assertion_id <> matching_assertion_id;
        return new;
    end if;

    select classification_assertion_id
      into prior_assertion_id
      from post_voice_classification_assertion
     where post_id = new.post_id
       and assertion_status_code = 'source'
       and valid_to is null
     order by recorded_at desc, classification_assertion_id
     limit 1;

    update post_voice_classification_assertion
       set valid_to = current_timestamp
     where post_id = new.post_id
       and assertion_status_code = 'source'
       and valid_to is null;

    insert into post_voice_classification_assertion (
        post_id, voice_concept_code, assertion_status_code,
        evidence_sha256, source_revision_digest, supersedes_assertion_id
    ) values (
        new.post_id, lower(new.voc_type_code), 'source',
        current_evidence_sha256, current_revision_digest, prior_assertion_id
    )
    on conflict (
        post_id, assertion_status_code, voice_concept_code,
        source_revision_digest
    ) where valid_to is null do nothing;
    return new;
end
$function$;

drop trigger if exists source_post_voice_assertion_reconcile on source_post;
create trigger source_post_voice_assertion_reconcile
after insert or update of voc_type_code, post_body on source_post
for each row execute function reconcile_post_voice_source_assertion();

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

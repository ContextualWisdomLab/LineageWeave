-- Migration 0257: provenance-bearing public-claim admission envelope.
-- Replay-safe under ADR 0166. Verification opt-in remains on global_ask_job.

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('public_claim_kind', 'claim_organization_presence', 'Organization presence', 0),
    ('public_claim_kind', 'claim_public_event', 'Public event', 1),
    ('public_claim_kind', 'claim_public_relationship', 'Public relationship', 2)
on conflict (lookup_code) do nothing;

create table if not exists public_claim_envelope (
    public_claim_envelope_id uuid primary key default uuid_generate_v4(),
    source_post_id uuid not null references source_post (post_id),
    provenance_assertion_id uuid not null references provenance_assertion (assertion_id),
    claim_kind_code text not null references common_lookup_value (lookup_code),
    claim_text text not null,
    egress_eligible boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (source_post_id, claim_kind_code, claim_text),
    check (char_length(btrim(claim_text)) between 1 and 800)
);

create index if not exists public_claim_envelope_egress_idx
    on public_claim_envelope (source_post_id, created_at)
    where egress_eligible;

create or replace function validate_public_claim_envelope()
returns trigger
language plpgsql
as $$
declare
    visibility text;
    claim_category text;
    evidence_post_id uuid;
    provenance_relation text;
begin
    select lookup_category into claim_category
      from common_lookup_value where lookup_code = new.claim_kind_code;
    if claim_category is distinct from 'public_claim_kind' then
        raise exception 'public_claim_kind_required';
    end if;

    select post.visibility_code into visibility
      from source_post post where post.post_id = new.source_post_id;
    select assertion.relation_code,
           case
               when count(binding.node_id) = 1
               then (array_agg(binding.node_id))[1]
           end
      into provenance_relation, evidence_post_id
      from provenance_assertion assertion
      left join provenance_resource_binding binding
        on binding.resource_id = assertion.object_resource_id
       and binding.node_type_code = 'node_post'
     where assertion.assertion_id = new.provenance_assertion_id
     group by assertion.relation_code;

    if new.egress_eligible and visibility is distinct from 'public' then
        raise exception 'public_claim_requires_public_post';
    end if;
    if provenance_relation is distinct from 'prov_was_derived_from'
       or evidence_post_id is distinct from new.source_post_id then
        raise exception 'public_claim_requires_source_post_provenance';
    end if;
    return new;
end;
$$;

drop trigger if exists validate_public_claim_envelope on public_claim_envelope;
create trigger validate_public_claim_envelope
    before insert or update on public_claim_envelope
    for each row execute function validate_public_claim_envelope();

create or replace function revoke_private_public_claim_envelopes()
returns trigger
language plpgsql
as $$
begin
    if old.visibility_code = 'public' and new.visibility_code <> 'public' then
        update public_claim_envelope
           set egress_eligible = false, updated_at = now()
         where source_post_id = new.post_id and egress_eligible;
    end if;
    return new;
end;
$$;

drop trigger if exists revoke_private_public_claim_envelopes on source_post;
create trigger revoke_private_public_claim_envelopes
    after update of visibility_code on source_post
    for each row execute function revoke_private_public_claim_envelopes();

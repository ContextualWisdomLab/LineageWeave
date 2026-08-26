-- ADR 0229: typed public-claim envelope for Global Ask verification.
-- Replay-safe (ADR 0166). Lookup rows and the envelope table are the
-- owning contract; private posts cannot be marked egress-eligible.

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('public_claim_kind', 'claim_organization_presence', 'Organization presence', 0),
    ('public_claim_kind', 'claim_public_event', 'Public event', 1),
    ('public_claim_kind', 'claim_public_relationship', 'Public relationship', 2),
    ('public_claim_verification_status', 'claim_unavailable', 'Unavailable', 0),
    ('public_claim_verification_status', 'claim_supported', 'Supported', 1),
    ('public_claim_verification_status', 'claim_refuted', 'Refuted', 2),
    ('public_claim_verification_status', 'claim_not_enough_information', 'Not enough information', 3),
    ('ontology_truth_status', 'truth_authoritative', 'Authoritative', 0),
    ('ontology_truth_status', 'truth_observed', 'Observed', 1),
    ('ontology_truth_status', 'truth_inferred', 'Inferred', 2),
    ('ontology_truth_status', 'truth_proposed', 'Proposed', 3),
    ('ontology_truth_status', 'truth_superseded', 'Superseded', 4),
    ('ontology_truth_status', 'truth_rejected', 'Rejected', 5)
on conflict (lookup_code) do nothing;

create table if not exists public_claim_envelope (
    public_claim_envelope_id uuid primary key default uuid_generate_v4(),
    source_post_id uuid not null references source_post (post_id),
    claim_kind_code text not null references common_lookup_value (lookup_code),
    subject_label text not null,
    claim_text text not null,
    truth_status_code text not null references common_lookup_value (lookup_code),
    event_occurred_at timestamptz,
    egress_eligible boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (source_post_id, claim_kind_code, claim_text),
    check (char_length(btrim(subject_label)) > 0),
    check (char_length(btrim(claim_text)) > 0)
);

create index if not exists public_claim_envelope_post_idx
    on public_claim_envelope (source_post_id);

create index if not exists public_claim_envelope_egress_idx
    on public_claim_envelope (egress_eligible)
    where egress_eligible;

comment on table public_claim_envelope is
    'Typed public claim bound to one source post. Egress-eligible rows may '
    'leave the trust boundary for SearXNG; person/Keyman/TEPP/fast-mlsirm '
    'kinds are not in the lookup and cannot be stored.';

create or replace function public_claim_envelope_require_public_post()
returns trigger
language plpgsql
as $$
declare
    vis text;
    claim_category text;
    truth_category text;
begin
    select lookup_category into claim_category
      from common_lookup_value
     where lookup_code = new.claim_kind_code;
    if claim_category is distinct from 'public_claim_kind' then
        raise exception 'claim_kind_code must belong to public_claim_kind';
    end if;
    select lookup_category into truth_category
      from common_lookup_value
     where lookup_code = new.truth_status_code;
    if truth_category is distinct from 'ontology_truth_status' then
        raise exception 'truth_status_code must belong to ontology_truth_status';
    end if;
    select visibility_code into vis
      from source_post
     where post_id = new.source_post_id;
    if vis is distinct from 'public' then
        if new.egress_eligible then
            raise exception 'egress_eligible requires a public source_post';
        end if;
        new.egress_eligible := false;
    end if;
    return new;
end;
$$;

drop trigger if exists public_claim_envelope_require_public_post
    on public_claim_envelope;
create trigger public_claim_envelope_require_public_post
    before insert or update on public_claim_envelope
    for each row
    execute function public_claim_envelope_require_public_post();

create or replace function public_claim_envelope_revoke_private_post()
returns trigger
language plpgsql
as $$
begin
    if old.visibility_code = 'public' and new.visibility_code <> 'public' then
        update public_claim_envelope
           set egress_eligible = false,
               updated_at = now()
         where source_post_id = new.post_id
           and egress_eligible;
    end if;
    return new;
end;
$$;

drop trigger if exists public_claim_envelope_revoke_private_post
    on source_post;
create trigger public_claim_envelope_revoke_private_post
    after update of visibility_code on source_post
    for each row
    execute function public_claim_envelope_revoke_private_post();

-- ADR 0224: typed public-claim envelope for Global Ask verification.
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
begin
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

do $$
begin
    if exists (
        select 1 from information_schema.tables
         where table_schema = 'public' and table_name = 'global_ask_job'
    ) then
        alter table global_ask_job
            add column if not exists verify_external boolean not null default false;
        comment on column global_ask_job.verify_external is
            'Opt-in public-claim verification. Off omits the projection; on '
            'loads authorized egress-eligible envelopes only.';
    end if;
end $$;

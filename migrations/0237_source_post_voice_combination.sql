-- ADR 0247: normalized, evidence-bearing Voice-of-X combinations.
-- source_post.voc_type_code remains the imported primary voice. Additional
-- voices require a normalized PROV-O assertion instead of keyword inference.

begin;

create table if not exists source_post_voice (
    post_id uuid not null references source_post (post_id) on delete cascade,
    voice_type_code text not null references common_lookup_value (lookup_code),
    is_primary boolean not null default false,
    truth_status_code text not null references common_lookup_value (lookup_code),
    provenance_assertion_id uuid references provenance_assertion (assertion_id),
    recorded_at timestamptz not null default now(),
    primary key (post_id, voice_type_code),
    check (is_primary or provenance_assertion_id is not null)
);

create unique index if not exists source_post_voice_primary_idx
    on source_post_voice (post_id) where is_primary;

create index if not exists source_post_voice_type_idx
    on source_post_voice (voice_type_code, post_id);

create or replace function validate_source_post_voice_codes()
returns trigger
language plpgsql
as $$
begin
    if not exists (
        select 1
        from common_lookup_value
        where lookup_category = 'voc_type'
          and lookup_code = new.voice_type_code
    ) then
        raise exception 'source_post_voice requires a voc_type lookup code'
            using errcode = '23514';
    end if;
    if not exists (
        select 1
        from common_lookup_value
        where lookup_category = 'ontology_truth_status'
          and lookup_code = new.truth_status_code
    ) then
        raise exception 'source_post_voice requires an ontology_truth_status lookup code'
            using errcode = '23514';
    end if;
    return new;
end;
$$;

drop trigger if exists source_post_voice_type_guard on source_post_voice;
create trigger source_post_voice_type_guard
before insert or update of voice_type_code, truth_status_code on source_post_voice
for each row execute function validate_source_post_voice_codes();

insert into source_post_voice
    (post_id, voice_type_code, is_primary, truth_status_code, recorded_at)
select post_id, voc_type_code, true, 'truth_observed', created_at
from source_post
on conflict (post_id, voice_type_code) do update
set is_primary = true,
    truth_status_code = 'truth_observed',
    provenance_assertion_id = null,
    recorded_at = least(source_post_voice.recorded_at, excluded.recorded_at);

create or replace function synchronize_source_post_primary_voice()
returns trigger
language plpgsql
as $$
begin
    delete from source_post_voice
    where post_id = new.post_id
      and is_primary
      and voice_type_code <> new.voc_type_code;

    insert into source_post_voice
        (post_id, voice_type_code, is_primary, truth_status_code)
    values (new.post_id, new.voc_type_code, true, 'truth_observed')
    on conflict (post_id, voice_type_code) do update
    set is_primary = true,
        truth_status_code = 'truth_observed',
        provenance_assertion_id = null;
    return new;
end;
$$;

drop trigger if exists source_post_primary_voice_sync on source_post;
create trigger source_post_primary_voice_sync
after insert or update of voc_type_code on source_post
for each row execute function synchronize_source_post_primary_voice();

commit;

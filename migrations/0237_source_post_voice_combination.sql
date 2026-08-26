-- ADR 0251: normalized, evidence-bearing Voice-of-X combinations.
-- source_post.voc_type_code remains the imported primary voice. Additional
-- voices require a normalized PROV-O assertion instead of keyword inference.

begin;

create table if not exists source_post_voice (
    voice_assignment_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post (post_id) on delete cascade,
    voice_type_code text not null references common_lookup_value (lookup_code),
    is_primary boolean not null default false,
    truth_status_code text not null references common_lookup_value (lookup_code),
    provenance_assertion_id uuid references provenance_assertion (assertion_id),
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    recorded_at timestamptz not null default now(),
    check (is_primary or provenance_assertion_id is not null),
    constraint source_post_voice_effective_interval_check
        check (effective_to is null or effective_to >= effective_from)
);

alter table source_post_voice
    add column if not exists voice_assignment_id uuid not null default gen_random_uuid();
alter table source_post_voice
    add column if not exists effective_from timestamptz not null default now();
alter table source_post_voice
    add column if not exists effective_to timestamptz;

do $$
begin
    if not exists (
        select 1 from pg_constraint
         where conrelid = 'source_post_voice'::regclass
           and conname = 'source_post_voice_effective_interval_check'
    ) then
        alter table source_post_voice
            add constraint source_post_voice_effective_interval_check
            check (effective_to is null or effective_to >= effective_from);
    end if;
end;
$$;

do $$
begin
    if exists (
        select 1 from pg_constraint
         where conrelid = 'source_post_voice'::regclass
           and contype = 'p'
           and pg_get_constraintdef(oid) <> 'PRIMARY KEY (voice_assignment_id)'
    ) then
        alter table source_post_voice drop constraint source_post_voice_pkey;
    end if;
    if not exists (
        select 1 from pg_constraint
         where conrelid = 'source_post_voice'::regclass and contype = 'p'
    ) then
        alter table source_post_voice
            add constraint source_post_voice_pkey primary key (voice_assignment_id);
    end if;
end;
$$;

drop index if exists source_post_voice_primary_idx;
create unique index if not exists source_post_voice_current_primary_idx
    on source_post_voice (post_id) where is_primary and effective_to is null;

create unique index if not exists source_post_voice_current_type_idx
    on source_post_voice (post_id, voice_type_code) where effective_to is null;

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
    if new.is_primary then
        perform 1 from source_post where post_id = new.post_id for update;
        if exists (
            select 1
              from source_post_voice existing
             where existing.post_id = new.post_id
               and existing.is_primary
               and existing.voice_assignment_id <> new.voice_assignment_id
               and tstzrange(existing.effective_from, existing.effective_to, '[)')
                   && tstzrange(new.effective_from, new.effective_to, '[)')
        ) then
            raise exception 'source_post_voice primary intervals must not overlap'
                using errcode = '23P01';
        end if;
    end if;
    return new;
end;
$$;

drop trigger if exists source_post_voice_type_guard on source_post_voice;
create trigger source_post_voice_type_guard
before insert or update on source_post_voice
for each row execute function validate_source_post_voice_codes();

insert into source_post_voice
    (post_id, voice_type_code, is_primary, truth_status_code, effective_from)
select post_id, voc_type_code, true, 'truth_observed', created_at
from source_post
on conflict (post_id, voice_type_code) where effective_to is null do update
set is_primary = true,
    truth_status_code = 'truth_observed',
    provenance_assertion_id = null
where not source_post_voice.is_primary;

create or replace function synchronize_source_post_primary_voice()
returns trigger
language plpgsql
as $$
declare
    change_at timestamptz := clock_timestamp();
begin
    update source_post_voice
       set effective_to = change_at
     where post_id = new.post_id
       and is_primary
       and effective_to is null
       and voice_type_code <> new.voc_type_code;

    insert into source_post_voice
        (post_id, voice_type_code, is_primary, truth_status_code, effective_from)
    values (
        new.post_id,
        new.voc_type_code,
        true,
        'truth_observed',
        case when tg_op = 'INSERT' then new.created_at else change_at end
    )
    on conflict (post_id, voice_type_code) where effective_to is null do update
    set is_primary = true,
        truth_status_code = 'truth_observed',
        provenance_assertion_id = null,
        effective_from = excluded.effective_from;
    return new;
end;
$$;

drop trigger if exists source_post_primary_voice_sync on source_post;
drop trigger if exists source_post_primary_voice_sync_insert on source_post;
create trigger source_post_primary_voice_sync_insert
after insert on source_post
for each row execute function synchronize_source_post_primary_voice();

create trigger source_post_primary_voice_sync
after update of voc_type_code on source_post
for each row
when (old.voc_type_code is distinct from new.voc_type_code)
execute function synchronize_source_post_primary_voice();

commit;

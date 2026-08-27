-- ADR 0252: preserve non-overlapping imported primary Voice intervals.

begin;

create extension if not exists btree_gist;

alter table source_post_voice
    add column if not exists effective_to timestamptz;

alter table source_post_voice
    drop constraint if exists source_post_voice_pkey;

alter table source_post_voice
    add primary key (post_id, voice_type_code, effective_from);

alter table source_post_voice
    drop constraint if exists source_post_voice_effective_interval_check;
alter table source_post_voice
    add constraint source_post_voice_effective_interval_check
    check (effective_to is null or effective_from < effective_to);

drop index if exists source_post_voice_primary_idx;
create unique index if not exists source_post_voice_current_pair_idx
    on source_post_voice (post_id, voice_type_code)
    where effective_to is null;

alter table source_post_voice
    drop constraint if exists source_post_voice_primary_period_excl;
alter table source_post_voice
    add constraint source_post_voice_primary_period_excl
    exclude using gist (
        post_id with =,
        tstzrange(effective_from, effective_to, '[)') with &&
    ) where (is_primary);

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
       and effective_to is null
       and (is_primary or voice_type_code = new.voc_type_code);

    insert into source_post_voice
        (post_id, voice_type_code, is_primary, truth_status_code,
         effective_from, recorded_at)
    values (
        new.post_id,
        new.voc_type_code,
        true,
        'truth_observed',
        case when tg_op = 'INSERT' then new.created_at else change_at end,
        change_at
    );
    return new;
end;
$$;

commit;

-- ADR 0362: row immutability must not be bypassable through TRUNCATE.
-- Draft-only ledgers may still be cleared; any published resource makes every
-- ledger relation part of immutable buyer-visible evidence.
begin;

create or replace function guard_ui_translation_truncate()
returns trigger
language plpgsql
as $$
begin
    if exists (
        select 1
          from ui_translation_resource
         where publication_state = 'published'
    ) then
        raise exception 'published UI translation resources are immutable and cannot be truncated';
    end if;
    return null;
end;
$$;

drop trigger if exists ui_translation_resource_truncate_guard on ui_translation_resource;
create trigger ui_translation_resource_truncate_guard
before truncate on ui_translation_resource
for each statement execute function guard_ui_translation_truncate();

drop trigger if exists ui_translation_key_truncate_guard on ui_translation_key;
create trigger ui_translation_key_truncate_guard
before truncate on ui_translation_key
for each statement execute function guard_ui_translation_truncate();

drop trigger if exists ui_translation_text_truncate_guard on ui_translation_text;
create trigger ui_translation_text_truncate_guard
before truncate on ui_translation_text
for each statement execute function guard_ui_translation_truncate();

commit;

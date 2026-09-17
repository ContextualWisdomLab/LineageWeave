-- Preserve reviewed Customer Master copy across replay of the historical 0248 seed.
-- The seed may fill missing rows, but once a migration-owned row exists, later
-- startup replays must not overwrite language/product review edits or trip the
-- immutable publication guard with a no-op historical seed update.
begin;

create or replace function preserve_customer_master_reviewed_seed_text_on_replay()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if current_setting('lineageweave.migration_file', true)
       is distinct from '0248_customer_master_translation_draft.sql' then
        return new;
    end if;

    if exists (
        select 1
          from ui_translation_seed_ownership as ownership
          join ui_translation_resource as resource
            on resource.resource_id = ownership.resource_id
         where ownership.migration_key = '0248_customer_master_translation_draft'
           and ownership.ownership_state = 'owned'
           and ownership.resource_id = old.resource_id
           and resource.product_key = 'lineageweave'
           and resource.screen_key = 'customer-master'
           and resource.resource_version = 1
    ) then
        -- Returning NULL from a BEFORE UPDATE trigger cancels this conflict
        -- update and prevents later mutation guards from interpreting replay of
        -- historical seed text as an attempted edit of an immutable publication.
        return null;
    end if;

    return new;
end;
$$;

drop trigger if exists customer_master_seed_reviewed_text_replay_guard
    on ui_translation_text;
create trigger customer_master_seed_reviewed_text_replay_guard
before update on ui_translation_text
for each row execute function preserve_customer_master_reviewed_seed_text_on_replay();

commit;

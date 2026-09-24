-- Harden generic UI translation child provenance for resource-id UPDATEs.
-- This companion migration runs after 0249_ui_translation_seed_ownership_generic.sql
-- and before the Similar VOC seed. A child UPDATE must not escape a seed-owned or
-- blocked resource by changing resource_id before the provenance lookup occurs.
begin;

create or replace function guard_ui_translation_seed_child_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    target_resource_id bigint;
    owner_migration_key text;
    owner_state text;
    owner_resource_id bigint;
    migration_file text;
begin
    migration_file := current_setting('lineageweave.migration_file', true);

    -- UPDATE is the only operation with two resource identities. Inspect the
    -- source before the target so changing resource_id cannot move a child out
    -- of a governed resource and thereby make the ownership join disappear.
    if tg_op = 'UPDATE' and old.resource_id is distinct from new.resource_id then
        select ownership.migration_key, ownership.ownership_state, ownership.resource_id
          into owner_migration_key, owner_state, owner_resource_id
          from public.ui_translation_resource as resource
          join public.ui_translation_seed_ownership as ownership
            on ownership.product_key = resource.product_key
           and ownership.screen_key = resource.screen_key
           and ownership.resource_version = resource.resource_version
         where resource.resource_id = old.resource_id
         for update of ownership;

        if owner_migration_key is not null
           and migration_file in (
               owner_migration_key || '.sql',
               'rollback/' || owner_migration_key || '.sql'
           ) then
            raise exception
                'UI translation seed % refuses child mutation outside exact seed ownership',
                owner_migration_key;
        end if;
    end if;

    if tg_op = 'DELETE' then
        target_resource_id := old.resource_id;
    else
        target_resource_id := new.resource_id;
    end if;

    owner_migration_key := null;
    owner_state := null;
    owner_resource_id := null;

    select ownership.migration_key, ownership.ownership_state, ownership.resource_id
      into owner_migration_key, owner_state, owner_resource_id
      from public.ui_translation_resource as resource
      join public.ui_translation_seed_ownership as ownership
        on ownership.product_key = resource.product_key
       and ownership.screen_key = resource.screen_key
       and ownership.resource_version = resource.resource_version
     where resource.resource_id = target_resource_id
     for update of ownership;

    if owner_migration_key is null then
        if tg_op = 'DELETE' then
            return old;
        end if;
        return new;
    end if;

    if migration_file = 'rollback/' || owner_migration_key || '.sql' then
        if tg_op <> 'DELETE'
           or owner_state <> 'owned'
           or owner_resource_id <> target_resource_id then
            raise exception
                'UI translation seed % refuses child mutation outside exact seed ownership',
                owner_migration_key;
        end if;
    elsif migration_file = owner_migration_key || '.sql'
       and (owner_state <> 'owned' or owner_resource_id <> target_resource_id) then
        raise exception
            'UI translation seed % refuses child mutation outside exact seed ownership',
            owner_migration_key;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

commit;

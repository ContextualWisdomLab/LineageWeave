-- Generalize one-time UI translation candidate ownership beyond Customer Master.
-- ADR 0362 keeps reviewed draft copy product-owned and prevents historical seed
-- bytes from becoming authoritative again after review or deliberate deletion.
begin;

create or replace function guard_ui_translation_seed_resource_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    owner_migration_key text;
    owner_state text;
    owner_resource_id bigint;
    migration_file text;
begin
    migration_file := current_setting('lineageweave.migration_file', true);

    if tg_op = 'INSERT' then
        select migration_key, ownership_state, resource_id
          into owner_migration_key, owner_state, owner_resource_id
          from public.ui_translation_seed_ownership
         where product_key = new.product_key
           and screen_key = new.screen_key
           and resource_version = new.resource_version
         for update;

        if owner_migration_key is null then
            return new;
        end if;

        if migration_file = owner_migration_key || '.sql' then
            if owner_state = 'blocked' then
                raise exception
                    'UI translation seed % refuses to adopt an existing unowned resource',
                    owner_migration_key;
            end if;
            if owner_state not in ('pending', 'owned') then
                raise exception
                    'UI translation seed % has no active ownership reservation',
                    owner_migration_key;
            end if;
            return new;
        end if;

        -- A pending row reserves this exact product/screen/version identity for
        -- its one-time seed. Once owned, blocked, or retired, ordinary product
        -- lifecycle remains outside migration provenance.
        if owner_state = 'pending' then
            raise exception
                'UI translation seed % reserves this resource identity until its migration runs',
                owner_migration_key;
        end if;
        return new;
    end if;

    select migration_key, ownership_state, resource_id
      into owner_migration_key, owner_state, owner_resource_id
      from public.ui_translation_seed_ownership
     where resource_id = old.resource_id
     for update;

    if owner_migration_key is null then
        return old;
    end if;

    if migration_file = 'rollback/' || owner_migration_key || '.sql' then
        if owner_state <> 'owned' or owner_resource_id <> old.resource_id then
            raise exception
                'UI translation rollback % refuses resource % outside exact seed ownership',
                owner_migration_key,
                old.resource_id;
        end if;
        return old;
    end if;

    if owner_state = 'owned' and owner_resource_id = old.resource_id then
        update public.ui_translation_seed_ownership
           set ownership_state = 'retired',
               resource_id = null
         where migration_key = owner_migration_key
           and ownership_state = 'owned'
           and resource_id = old.resource_id;
    end if;
    return old;
end;
$$;

create or replace function bind_ui_translation_seed_resource_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    owner_migration_key text;
    owner_state text;
    owner_resource_id bigint;
    migration_file text;
begin
    migration_file := current_setting('lineageweave.migration_file', true);

    select migration_key, ownership_state, resource_id
      into owner_migration_key, owner_state, owner_resource_id
      from public.ui_translation_seed_ownership
     where product_key = new.product_key
       and screen_key = new.screen_key
       and resource_version = new.resource_version
     for update;

    if owner_migration_key is null
       or migration_file is distinct from owner_migration_key || '.sql' then
        return new;
    end if;

    if owner_state = 'owned' and owner_resource_id = new.resource_id then
        return new;
    end if;

    update public.ui_translation_seed_ownership
       set ownership_state = 'owned',
           resource_id = new.resource_id
     where migration_key = owner_migration_key
       and ownership_state = 'pending'
       and resource_id is null;

    if not found then
        raise exception
            'UI translation seed % could not bind ownership to resource %',
            owner_migration_key,
            new.resource_id;
    end if;
    return new;
end;
$$;

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
    if tg_op = 'DELETE' then
        target_resource_id := old.resource_id;
    else
        target_resource_id := new.resource_id;
    end if;

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

    migration_file := current_setting('lineageweave.migration_file', true);
    if migration_file = owner_migration_key || '.sql'
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

-- Replace the Customer-Master-specific trigger wiring with the same generic
-- lifecycle boundary. The legacy functions remain harmlessly defined so old
-- rollback evidence stays inspectable, but they are no longer active writers.
drop trigger if exists customer_master_seed_resource_ownership_guard
    on public.ui_translation_resource;
drop trigger if exists customer_master_seed_resource_ownership_bind
    on public.ui_translation_resource;
drop trigger if exists customer_master_seed_key_ownership_guard
    on public.ui_translation_key;
drop trigger if exists customer_master_seed_text_ownership_guard
    on public.ui_translation_text;

drop trigger if exists ui_translation_seed_resource_ownership_guard
    on public.ui_translation_resource;
create trigger ui_translation_seed_resource_ownership_guard
before insert or delete on public.ui_translation_resource
for each row execute function guard_ui_translation_seed_resource_ownership();

drop trigger if exists ui_translation_seed_resource_ownership_bind
    on public.ui_translation_resource;
create trigger ui_translation_seed_resource_ownership_bind
after insert on public.ui_translation_resource
for each row execute function bind_ui_translation_seed_resource_ownership();

drop trigger if exists ui_translation_seed_key_ownership_guard
    on public.ui_translation_key;
create trigger ui_translation_seed_key_ownership_guard
before insert or update or delete on public.ui_translation_key
for each row execute function guard_ui_translation_seed_child_ownership();

drop trigger if exists ui_translation_seed_text_ownership_guard
    on public.ui_translation_text;
create trigger ui_translation_seed_text_ownership_guard
before insert or update or delete on public.ui_translation_text
for each row execute function guard_ui_translation_seed_child_ownership();

-- Reserve Similar VOC v1 before the seed can touch reviewable copy. A resource
-- that predates this reservation is operator-owned and remains fail-closed.
do $similar_voc_seed_ownership_init$
declare
    owner_state text;
    owner_resource_id bigint;
    owner_product_key text;
    owner_screen_key text;
    owner_resource_version bigint;
    target_resource_id bigint;
begin
    insert into public.ui_translation_seed_ownership(
        migration_key,
        product_key,
        screen_key,
        resource_version,
        ownership_state
    )
    select
        '0249_z_similar_voc_translation_draft',
        'lineageweave',
        'similar-voc',
        1,
        case
            when exists (
                select 1
                  from public.ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'similar-voc'
                   and resource_version = 1
            ) then 'blocked'
            else 'pending'
        end
    on conflict (migration_key) do nothing;

    select ownership_state, resource_id, product_key, screen_key, resource_version
      into owner_state, owner_resource_id, owner_product_key, owner_screen_key,
           owner_resource_version
      from public.ui_translation_seed_ownership
     where migration_key = '0249_z_similar_voc_translation_draft'
     for update;

    if owner_state is null then
        raise exception 'Similar VOC translation seed ownership reservation is missing';
    end if;

    if owner_product_key <> 'lineageweave'
       or owner_screen_key <> 'similar-voc'
       or owner_resource_version <> 1 then
        raise exception 'Similar VOC translation seed ownership identity drifted';
    end if;

    select resource_id
      into target_resource_id
      from public.ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'similar-voc'
       and resource_version = 1
     for update;

    if owner_state = 'retired' then
        if owner_resource_id is not null then
            raise exception 'Retired Similar VOC seed unexpectedly retains resource %',
                owner_resource_id;
        end if;
        return;
    end if;

    if owner_state = 'owned' then
        if target_resource_id is distinct from owner_resource_id then
            raise exception
                'Similar VOC seed ownership points to resource %, current resource is %',
                owner_resource_id,
                target_resource_id;
        end if;
        return;
    end if;

    if owner_state = 'blocked' and target_resource_id is null then
        update public.ui_translation_seed_ownership
           set ownership_state = 'pending'
         where migration_key = '0249_z_similar_voc_translation_draft';
        return;
    end if;

    if owner_state = 'pending' and target_resource_id is not null then
        raise exception
            'Similar VOC seed pending ownership collided with existing resource %',
            target_resource_id;
    end if;
end;
$similar_voc_seed_ownership_init$;

commit;

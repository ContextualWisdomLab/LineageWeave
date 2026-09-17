-- Reserve Customer Master v1 seed ownership before 0248 can touch its draft.
-- A pre-existing resource remains operator-owned and is never adopted implicitly.
begin;

create table if not exists ui_translation_seed_ownership (
    migration_key text primary key,
    product_key text not null,
    screen_key text not null,
    resource_version bigint not null check (resource_version > 0),
    resource_id bigint unique
        references ui_translation_resource(resource_id) on delete cascade,
    ownership_state text not null,
    constraint ui_translation_seed_ownership_state_ck
        check (ownership_state in ('pending', 'owned', 'blocked', 'retired')),
    unique (product_key, screen_key, resource_version),
    constraint ui_translation_seed_ownership_shape_ck
        check (
            (ownership_state = 'owned' and resource_id is not null)
            or (
                ownership_state in ('pending', 'blocked', 'retired')
                and resource_id is null
            )
        )
);

-- Existing installations predate the retired one-time-seed receipt. Upgrade only
-- the two ownership-state checks once; subsequent migration replay stays metadata-only.
do $customer_master_seed_ownership_retirement_contract$
declare
    stale_constraint text;
begin
    for stale_constraint in
        select conname
          from pg_constraint
         where conrelid = 'public.ui_translation_seed_ownership'::regclass
           and contype = 'c'
           and pg_get_constraintdef(oid) like '%ownership_state%'
           and conname not in (
               'ui_translation_seed_ownership_state_ck',
               'ui_translation_seed_ownership_shape_ck'
           )
    loop
        execute format(
            'alter table public.ui_translation_seed_ownership drop constraint %I',
            stale_constraint
        );
    end loop;

    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.ui_translation_seed_ownership'::regclass
           and conname = 'ui_translation_seed_ownership_state_ck'
    ) then
        alter table public.ui_translation_seed_ownership
            add constraint ui_translation_seed_ownership_state_ck
            check (ownership_state in ('pending', 'owned', 'blocked', 'retired'));
    end if;

    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.ui_translation_seed_ownership'::regclass
           and conname = 'ui_translation_seed_ownership_shape_ck'
    ) then
        alter table public.ui_translation_seed_ownership
            add constraint ui_translation_seed_ownership_shape_ck
            check (
                (ownership_state = 'owned' and resource_id is not null)
                or (
                    ownership_state in ('pending', 'blocked', 'retired')
                    and resource_id is null
                )
            );
    end if;
end;
$customer_master_seed_ownership_retirement_contract$;

do $customer_master_seed_ownership_init$
declare
    target_resource_id bigint;
    owner_state text;
    owner_resource_id bigint;
    owner_product_key text;
    owner_screen_key text;
    owner_resource_version bigint;
begin
    -- A replay can overlap a transaction that has already reserved this
    -- migration key but has not committed yet. The unique index is the
    -- serialization point: wait for that owner, then inspect the committed
    -- reservation instead of failing startup with a duplicate-key error.
    insert into ui_translation_seed_ownership(
        migration_key,
        product_key,
        screen_key,
        resource_version,
        ownership_state
    )
    select
        '0248_customer_master_translation_draft',
        'lineageweave',
        'customer-master',
        1,
        case
            when exists (
                select 1
                  from ui_translation_resource
                 where product_key = 'lineageweave'
                   and screen_key = 'customer-master'
                   and resource_version = 1
            ) then 'blocked'
            else 'pending'
        end
    on conflict (migration_key) do nothing;

    select ownership_state, resource_id, product_key, screen_key, resource_version
      into owner_state, owner_resource_id, owner_product_key, owner_screen_key,
           owner_resource_version
      from ui_translation_seed_ownership
     where migration_key = '0248_customer_master_translation_draft'
     for update;

    if owner_state is null then
        raise exception
            'Customer Master seed ownership reservation is missing after initialization';
    end if;

    if owner_product_key <> 'lineageweave'
       or owner_screen_key <> 'customer-master'
       or owner_resource_version <> 1 then
        raise exception
            'Customer Master seed ownership identity drifted from migration 0248';
    end if;

    -- An ordinary product delete after successful materialization retires the
    -- one-time seed. Preserve that receipt without touching any later
    -- operator-owned resource that might reuse the product identity.
    if owner_state = 'retired' then
        if owner_resource_id is not null then
            raise exception
                'Retired Customer Master seed ownership unexpectedly retains resource %',
                owner_resource_id;
        end if;
        return;
    end if;

    -- Lock the product resource only after the ownership row. Trigger paths
    -- also consult ownership before binding a new resource, so this keeps a
    -- single lock order for replay and seed creation.
    select resource_id
      into target_resource_id
      from ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'customer-master'
       and resource_version = 1
     for update;

    if owner_state = 'owned' then
        if target_resource_id is distinct from owner_resource_id then
            raise exception
                'Customer Master seed ownership points to resource %, current resource is %',
                owner_resource_id,
                target_resource_id;
        end if;
        return;
    end if;

    if owner_state = 'blocked' and target_resource_id is null then
        update ui_translation_seed_ownership
           set ownership_state = 'pending'
         where migration_key = '0248_customer_master_translation_draft';
        return;
    end if;

    if owner_state = 'pending' and target_resource_id is not null then
        raise exception
            'Customer Master seed pending ownership collided with existing resource %',
            target_resource_id;
    end if;
end;
$customer_master_seed_ownership_init$;

create or replace function guard_customer_master_seed_resource_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    owner_state text;
    migration_file text;
begin
    migration_file := current_setting('lineageweave.migration_file', true);

    if tg_op = 'INSERT' then
        if new.product_key <> 'lineageweave'
           or new.screen_key <> 'customer-master'
           or new.resource_version <> 1 then
            return new;
        end if;

        select ownership_state
          into owner_state
          from ui_translation_seed_ownership
         where migration_key = '0248_customer_master_translation_draft'
         for update;

        if migration_file = '0248_customer_master_translation_draft.sql' then
            if owner_state = 'blocked' then
                raise exception
                    'Customer Master seed refuses to adopt existing unowned Customer Master resource';
            end if;
            if owner_state not in ('pending', 'owned') then
                raise exception
                    'Customer Master seed has no valid ownership reservation';
            end if;
            return new;
        end if;

        -- pending reserves this exact identity until 0248 creates it. Once a
        -- resource is blocked/owned/retired, ordinary product identity lifecycle
        -- remains outside migration provenance.
        if owner_state = 'pending' then
            raise exception
                'Customer Master seed refuses to create resource outside migration 0248 ownership context';
        end if;
        return new;
    end if;

    if old.product_key <> 'lineageweave'
       or old.screen_key <> 'customer-master'
       or old.resource_version <> 1 then
        return old;
    end if;

    -- A normal delete after the migration has materialized its candidate means
    -- the reviewer/operator intentionally retired that review object. Detach the
    -- FK before root deletion so ON DELETE CASCADE cannot erase the one-time
    -- completion receipt and silently re-authorize historical seed bytes.
    if migration_file is distinct from 'rollback/0248_customer_master_translation_draft.sql' then
        update ui_translation_seed_ownership
           set ownership_state = 'retired',
               resource_id = null
         where migration_key = '0248_customer_master_translation_draft'
           and ownership_state = 'owned'
           and resource_id = old.resource_id;
        return old;
    end if;

    -- Ownership constrains the 0248 rollback, not ordinary product/operator
    -- lifecycle operations on a pre-existing resource. A deliberate 0248
    -- rollback removes only the resource that this migration still owns.
    if not exists (
        select 1
          from ui_translation_seed_ownership
         where migration_key = '0248_customer_master_translation_draft'
           and ownership_state = 'owned'
           and resource_id = old.resource_id
    ) then
        raise exception
            'Customer Master translation rollback refuses to remove unowned Customer Master resource %',
            old.resource_id;
    end if;
    return old;
end;
$$;

create or replace function bind_customer_master_seed_resource_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if new.product_key <> 'lineageweave'
       or new.screen_key <> 'customer-master'
       or new.resource_version <> 1 then
        return new;
    end if;

    if current_setting('lineageweave.migration_file', true)
       is distinct from '0248_customer_master_translation_draft.sql' then
        return new;
    end if;

    update ui_translation_seed_ownership
       set ownership_state = 'owned',
           resource_id = new.resource_id
     where migration_key = '0248_customer_master_translation_draft'
       and ownership_state = 'pending'
       and resource_id is null;

    if not found then
        raise exception
            'Customer Master seed could not bind migration ownership to resource %',
            new.resource_id;
    end if;
    return new;
end;
$$;

create or replace function guard_customer_master_seed_child_ownership()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    target_resource_id bigint;
    target_is_customer_master boolean;
begin
    -- The ownership invariant is a migration-0248 boundary. It must not seize
    -- ordinary draft editing/deletion authority from an operator-owned resource.
    if current_setting('lineageweave.migration_file', true)
       is distinct from '0248_customer_master_translation_draft.sql' then
        if tg_op = 'DELETE' then
            return old;
        end if;
        return new;
    end if;

    if tg_op = 'DELETE' then
        target_resource_id := old.resource_id;
    else
        target_resource_id := new.resource_id;
    end if;

    select exists (
        select 1
          from ui_translation_resource
         where resource_id = target_resource_id
           and product_key = 'lineageweave'
           and screen_key = 'customer-master'
           and resource_version = 1
    ) into target_is_customer_master;

    if target_is_customer_master
       and not exists (
           select 1
             from ui_translation_seed_ownership
            where migration_key = '0248_customer_master_translation_draft'
              and ownership_state = 'owned'
              and resource_id = target_resource_id
       ) then
        raise exception
            'Customer Master seed refuses to adopt existing unowned Customer Master resource %',
            target_resource_id;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

do $customer_master_seed_ownership_triggers$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'ui_translation_resource'::regclass
           and tgname = 'customer_master_seed_resource_ownership_guard'
           and not tgisinternal
    ) then
        create trigger customer_master_seed_resource_ownership_guard
        before insert or delete on ui_translation_resource
        for each row execute function guard_customer_master_seed_resource_ownership();
    end if;

    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'ui_translation_resource'::regclass
           and tgname = 'customer_master_seed_resource_ownership_bind'
           and not tgisinternal
    ) then
        create trigger customer_master_seed_resource_ownership_bind
        after insert on ui_translation_resource
        for each row execute function bind_customer_master_seed_resource_ownership();
    end if;

    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'ui_translation_key'::regclass
           and tgname = 'customer_master_seed_key_ownership_guard'
           and not tgisinternal
    ) then
        create trigger customer_master_seed_key_ownership_guard
        before insert or update or delete on ui_translation_key
        for each row execute function guard_customer_master_seed_child_ownership();
    end if;

    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'ui_translation_text'::regclass
           and tgname = 'customer_master_seed_text_ownership_guard'
           and not tgisinternal
    ) then
        create trigger customer_master_seed_text_ownership_guard
        before insert or update or delete on ui_translation_text
        for each row execute function guard_customer_master_seed_child_ownership();
    end if;
end;
$customer_master_seed_ownership_triggers$;

commit;

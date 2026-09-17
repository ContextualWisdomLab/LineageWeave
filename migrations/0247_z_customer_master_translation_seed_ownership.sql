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
    ownership_state text not null
        check (ownership_state in ('pending', 'owned', 'blocked')),
    unique (product_key, screen_key, resource_version),
    check (
        (ownership_state = 'owned' and resource_id is not null)
        or (ownership_state in ('pending', 'blocked') and resource_id is null)
    )
);

do $customer_master_seed_ownership_init$
declare
    target_resource_id bigint;
    owner_state text;
    owner_resource_id bigint;
    owner_product_key text;
    owner_screen_key text;
    owner_resource_version bigint;
begin
    select resource_id
      into target_resource_id
      from ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'customer-master'
       and resource_version = 1
     for update;

    select ownership_state, resource_id, product_key, screen_key, resource_version
      into owner_state, owner_resource_id, owner_product_key, owner_screen_key,
           owner_resource_version
      from ui_translation_seed_ownership
     where migration_key = '0248_customer_master_translation_draft'
     for update;

    if owner_state is null then
        insert into ui_translation_seed_ownership(
            migration_key,
            product_key,
            screen_key,
            resource_version,
            ownership_state
        )
        values (
            '0248_customer_master_translation_draft',
            'lineageweave',
            'customer-master',
            1,
            case when target_resource_id is null then 'pending' else 'blocked' end
        );
        return;
    end if;

    if owner_product_key <> 'lineageweave'
       or owner_screen_key <> 'customer-master'
       or owner_resource_version <> 1 then
        raise exception
            'Customer Master seed ownership identity drifted from migration 0248';
    end if;

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
as $$
declare
    owner_state text;
    migration_file text;
begin
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
        migration_file := current_setting('lineageweave.migration_file', true);

        if owner_state is distinct from 'pending'
           or migration_file is distinct from '0248_customer_master_translation_draft.sql' then
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
as $$
begin
    if new.product_key <> 'lineageweave'
       or new.screen_key <> 'customer-master'
       or new.resource_version <> 1 then
        return new;
    end if;

    if current_setting('lineageweave.migration_file', true)
       is distinct from '0248_customer_master_translation_draft.sql' then
        raise exception
            'Customer Master seed refuses to bind ownership outside migration 0248 context';
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
as $$
declare
    target_resource_id bigint;
    target_is_customer_master boolean;
begin
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

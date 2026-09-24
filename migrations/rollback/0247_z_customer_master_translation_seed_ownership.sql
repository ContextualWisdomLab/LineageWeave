-- Remove the Customer Master seed-ownership boundary only after its resource is gone.
begin;

do $customer_master_seed_ownership_rollback$
begin
    if exists (
        select 1
          from ui_translation_resource
         where product_key = 'lineageweave'
           and screen_key = 'customer-master'
           and resource_version = 1
    ) then
        raise exception
            'Customer Master seed ownership rollback refuses while v1 resource exists';
    end if;

    -- A reservation that never created or adopted product data can be released.
    -- A retired receipt is different: it is the durable no-resurrection fact
    -- that historical 0248 bytes have already completed their lifecycle.
    delete from ui_translation_seed_ownership
     where migration_key = '0248_customer_master_translation_draft'
       and ownership_state in ('pending', 'blocked')
       and resource_id is null;

    if exists (
        select 1
          from ui_translation_seed_ownership
         where migration_key = '0248_customer_master_translation_draft'
           and ownership_state = 'retired'
           and resource_id is null
    ) then
        raise exception
            'Customer Master seed ownership rollback refuses to erase retired no-resurrection history';
    end if;

    if exists (select 1 from ui_translation_seed_ownership) then
        raise exception
            'Customer Master seed ownership rollback refuses while ownership records remain';
    end if;
end;
$customer_master_seed_ownership_rollback$;

drop trigger if exists customer_master_seed_text_ownership_guard
    on ui_translation_text;
drop trigger if exists customer_master_seed_key_ownership_guard
    on ui_translation_key;
drop trigger if exists customer_master_seed_resource_ownership_bind
    on ui_translation_resource;
drop trigger if exists customer_master_seed_resource_ownership_guard
    on ui_translation_resource;

drop function if exists guard_customer_master_seed_child_ownership();
drop function if exists bind_customer_master_seed_resource_ownership();
drop function if exists guard_customer_master_seed_resource_ownership();
drop table if exists ui_translation_seed_ownership;

commit;

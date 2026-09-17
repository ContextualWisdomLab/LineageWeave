-- Roll back only the unpublished Customer Master v1 review draft.
begin;

do $customer_master_seed_rollback$
declare
    target_resource_id bigint;
    target_state text;
begin
    select resource_id, publication_state
      into target_resource_id, target_state
      from ui_translation_resource
     where product_key = 'lineageweave'
       and screen_key = 'customer-master'
       and resource_version = 1;

    if target_resource_id is null then
        return;
    end if;

    if target_state <> 'draft' then
        raise exception
            'Customer Master translation rollback refuses to remove published resource %',
            target_resource_id;
    end if;

    delete from ui_translation_resource
     where resource_id = target_resource_id;
end;
$customer_master_seed_rollback$;

commit;

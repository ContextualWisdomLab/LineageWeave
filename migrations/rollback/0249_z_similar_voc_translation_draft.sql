-- Roll back only the unpublished Similar VOC v1 resource owned by its seed.
begin;

select set_config(
    'lineageweave.migration_file',
    'rollback/0249_z_similar_voc_translation_draft.sql',
    true
);

do $similar_voc_seed_rollback$
declare
    owner_state text;
    owner_resource_id bigint;
    target_state text;
    target_product_key text;
    target_screen_key text;
    target_resource_version bigint;
begin
    select ownership_state, resource_id
      into owner_state, owner_resource_id
      from public.ui_translation_seed_ownership
     where migration_key = '0249_z_similar_voc_translation_draft'
       and product_key = 'lineageweave'
       and screen_key = 'similar-voc'
       and resource_version = 1
     for update;

    if owner_state is null or owner_state in ('blocked', 'retired') then
        return;
    end if;

    if owner_state = 'pending' then
        delete from public.ui_translation_seed_ownership
         where migration_key = '0249_z_similar_voc_translation_draft'
           and ownership_state = 'pending'
           and resource_id is null;
        return;
    end if;

    if owner_state <> 'owned' or owner_resource_id is null then
        raise exception 'Similar VOC translation rollback has invalid ownership state %',
            owner_state;
    end if;

    select publication_state, product_key, screen_key, resource_version
      into target_state, target_product_key, target_screen_key, target_resource_version
      from public.ui_translation_resource
     where resource_id = owner_resource_id
     for update;

    if target_state is null then
        raise exception
            'Similar VOC translation rollback ownership points to missing resource %',
            owner_resource_id;
    end if;

    if target_product_key <> 'lineageweave'
       or target_screen_key <> 'similar-voc'
       or target_resource_version <> 1 then
        raise exception
            'Similar VOC translation rollback refuses resource % with drifted identity',
            owner_resource_id;
    end if;

    if target_state <> 'draft' then
        raise exception
            'Similar VOC translation rollback refuses to remove published resource %',
            owner_resource_id;
    end if;

    delete from public.ui_translation_resource
     where resource_id = owner_resource_id;
end;
$similar_voc_seed_rollback$;

commit;

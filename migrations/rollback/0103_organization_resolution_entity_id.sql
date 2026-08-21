begin;

drop index if exists organization_name_resolution_entity_id_idx;
alter table organization_name_resolution
    drop column if exists resolved_corporate_entity_id;

commit;

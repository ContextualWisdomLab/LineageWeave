-- Fail-closed rollback for migration 0023.
--
-- Drops the persisted person catalog identity on post_summary_role.
-- Team and organization columns from 0019 remain.

alter table if exists post_summary_role
    drop constraint if exists post_summary_role_catalog_type_chk,
    drop constraint if exists post_summary_role_one_catalog_chk,
    drop column if exists cataloged_person_id;

-- Fail-closed rollback for migration 0019.
--
-- Drops the persisted catalog identity columns on post_summary_role.
-- Re-running after a successful rollback is safe.

alter table if exists post_summary_role
    drop constraint if exists post_summary_role_catalog_type_chk,
    drop constraint if exists post_summary_role_one_catalog_chk,
    drop column if exists cataloged_person_id,
    drop column if exists corporate_entity_id,
    drop column if exists cataloged_team_id;
